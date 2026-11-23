"""
GreenCloud Web Application & Enterprise API Backend.
Provides RESTful APIs for real-time monitoring, intelligent right-sizing,
sustainability analysis, and interactive simulation.
"""

import os
import sys
import time
import platform
from flask import Flask, jsonify, request, render_template, Response
import psutil

from advisor import advise
from engine.collector import (
    get_collector,
    CollectorSnapshot,
    SOURCE_CGROUP_V2,
    SOURCE_CGROUP_V1,
    SOURCE_HOST,
)
from engine.models import WorkloadSpec, ResourceMetrics
from engine.advisor import analyze_and_recommend, run_full_audit
from engine.carbon import (
    estimate_carbon_footprint,
    REGIONAL_GRID_INTENSITY,
    PUE_PUBLIC_CLOUD,
    PUE_PRIVATE_CLOUD,
)
from engine.prometheus import format_prometheus_metrics, PROMETHEUS_CONTENT_TYPE

app = Flask(__name__)

# Deployment baseline settings
CPU_REQUEST_M = 10     # Reserved in deployment.yaml
CPU_LIMIT_M = 100      # Limit in deployment.yaml
MEM_REQUEST_MIB = 64   # Reserved in deployment.yaml
MEM_LIMIT_MIB = 128    # Limit in deployment.yaml
REPLICAS = 2

# Process-wide background collector singleton
collector = get_collector()
APP_START_TIME = time.time()


# ---------------------------------------------------------------------------
# Legacy Backward Compatibility Helper
# ---------------------------------------------------------------------------
def read_cpu_usec():
    """Maintained for backward-compatibility with direct function tests."""
    try:
        with open("/sys/fs/cgroup/cpu.stat") as f:
            for line in f:
                if line.startswith("usage_usec"):
                    return int(line.split()[1])
    except (FileNotFoundError, OSError, PermissionError):
        pass
    return None


def get_advice():
    """Non-blocking advice generation powered by background collector."""
    metrics = collector.get_resource_metrics()
    return advise(REPLICAS, metrics.cpu_used_m, CPU_REQUEST_M, max(metrics.cpu_peak_m, 1.0))


# ---------------------------------------------------------------------------
# Core Routes
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    """Renders the Enterprise GreenCloud Web Dashboard."""
    return render_template("dashboard.html")


@app.route("/metrics")
def metrics():
    """
    Genuine Prometheus metrics endpoint.
    Returns standard Prometheus text exposition format (text/plain; version=0.0.4)
    when scraped by Prometheus or by default.
    Returns JSON when requested via ?format=json or Accept: application/json.
    """
    snapshot = collector.get_snapshot()

    # Content negotiation: return JSON if requested
    fmt = request.args.get("format", "").lower()
    accept = request.headers.get("Accept", "").lower()
    if fmt == "json" or "application/json" in accept:
        return jsonify(
            cpu_percent=snapshot.cpu_percent,
            memory_percent=snapshot.mem_percent,
            cpu_used_m=snapshot.cpu_used_m,
            cpu_peak_m=snapshot.cpu_peak_m,
            mem_used_mib=snapshot.mem_used_mib,
            metric_source=snapshot.metric_source,
            is_container=snapshot.is_container,
        )

    # Standard Prometheus text exposition format
    spec = WorkloadSpec(
        name="greencloud",
        namespace="default",
        replicas=REPLICAS,
        cpu_request_m=CPU_REQUEST_M,
        cpu_limit_m=CPU_LIMIT_M,
        mem_request_mib=MEM_REQUEST_MIB,
        mem_limit_mib=MEM_LIMIT_MIB,
        is_simulated=False
    )
    metrics_obj = ResourceMetrics(
        cpu_used_m=snapshot.cpu_used_m,
        cpu_peak_m=max(snapshot.cpu_peak_m, snapshot.cpu_used_m, 1.0),
        mem_used_mib=snapshot.mem_used_mib,
        mem_peak_mib=max(snapshot.mem_peak_mib, snapshot.mem_used_mib, 16.0),
        is_simulated=False
    )
    audit = run_full_audit(spec, metrics_obj, grid_region="india")
    prom_text = format_prometheus_metrics(snapshot, audit)
    return Response(prom_text, mimetype=PROMETHEUS_CONTENT_TYPE)


# ---------------------------------------------------------------------------
# Enterprise REST APIs for Dashboard & Analytics
# ---------------------------------------------------------------------------
@app.route("/api/snapshot")
def api_snapshot():
    """Returns the latest non-blocking snapshot and historical telemetry."""
    snapshot = collector.get_snapshot()
    history = collector.get_history(limit=60)
    return jsonify(
        snapshot=snapshot.to_dict(),
        history=history,
        server_time=time.time()
    )


def _get_demo_workloads():
    """Returns realistic enterprise demonstration workloads, strictly tagged as simulated."""
    return [
        {
            "id": "auth-service",
            "name": "auth-service-prod",
            "namespace": "production",
            "replicas": 3,
            "cpu_request_m": 500,
            "cpu_limit_m": 1000,
            "mem_request_mib": 1024,
            "mem_limit_mib": 2048,
            "is_simulated": True,
            "status": "Running",
            "metrics": {
                "cpu_used_m": 45.0,
                "cpu_peak_m": 115.0,
                "mem_used_mib": 185.0,
                "mem_peak_mib": 250.0,
                "cpu_percent": 9.0,
                "mem_percent": 18.1,
            },
            "metric_source": "synthetic_demo",
            "is_container": True,
            "description": "OAuth 2.0 / JWT session authentication cluster (Heavily over-provisioned)"
        },
        {
            "id": "analytics-worker",
            "name": "analytics-batch-ingestor",
            "namespace": "analytics",
            "replicas": 1,
            "cpu_request_m": 200,
            "cpu_limit_m": 400,
            "mem_request_mib": 512,
            "mem_limit_mib": 1024,
            "is_simulated": True,
            "status": "Warning (High Load)",
            "metrics": {
                "cpu_used_m": 188.0,
                "cpu_peak_m": 385.0,
                "mem_used_mib": 490.0,
                "mem_peak_mib": 960.0,
                "cpu_percent": 94.0,
                "mem_percent": 95.7,
            },
            "metric_source": "synthetic_demo",
            "is_container": True,
            "description": "Real-time streaming ingestion pipeline (Critical under-provisioning / OOM risk)"
        },
        {
            "id": "redis-cache",
            "name": "redis-cluster-node",
            "namespace": "cache",
            "replicas": 2,
            "cpu_request_m": 150,
            "cpu_limit_m": 300,
            "mem_request_mib": 512,
            "mem_limit_mib": 1024,
            "is_simulated": True,
            "status": "Healthy",
            "metrics": {
                "cpu_used_m": 62.0,
                "cpu_peak_m": 88.0,
                "mem_used_mib": 245.0,
                "mem_peak_mib": 310.0,
                "cpu_percent": 41.3,
                "mem_percent": 47.8,
            },
            "metric_source": "synthetic_demo",
            "is_container": True,
            "description": "In-memory database caching tier (Healthy / Optimal resource efficiency)"
        }
    ]


@app.route("/api/workloads")
def api_workloads():
    """
    Returns all workloads, clearly separating the genuine LIVE workload
    from the DEMO simulated workloads.
    """
    snap = collector.get_snapshot()

    # 1. Real Monitored Workload
    live_workload = {
        "id": "greencloud-live",
        "name": "greencloud-web-deployment",
        "namespace": "default",
        "replicas": REPLICAS,
        "cpu_request_m": CPU_REQUEST_M,
        "cpu_limit_m": CPU_LIMIT_M,
        "mem_request_mib": MEM_REQUEST_MIB,
        "mem_limit_mib": MEM_LIMIT_MIB,
        "is_simulated": False,  # GENUINE LIVE MEASUREMENT
        "status": "Active",
        "metrics": {
            "cpu_used_m": snap.cpu_used_m,
            "cpu_peak_m": snap.cpu_peak_m,
            "mem_used_mib": snap.mem_used_mib,
            "mem_peak_mib": snap.mem_peak_mib,
            "cpu_percent": snap.cpu_percent,
            "mem_percent": snap.mem_percent,
        },
        "metric_source": snap.metric_source,
        "is_container": snap.is_container,
        "description": "Your actual live container or local host environment"
    }

    # 2. Demonstration Workloads
    demo_workloads = _get_demo_workloads()

    return jsonify(
        live_workload=live_workload,
        demo_workloads=demo_workloads,
        total_count=1 + len(demo_workloads),
        collector_source=snap.metric_source
    )


@app.route("/api/audit", methods=["POST"])
def api_audit():
    """
    Runs an intelligent optimization, sustainability, and FinOps audit for a workload.
    """
    data = request.get_json() or {}
    workload_id = data.get("workload_id", "greencloud-live")
    grid_region = data.get("grid_region", "global")
    pue = float(data.get("pue", PUE_PUBLIC_CLOUD))

    # Retrieve or build target spec and metrics
    if workload_id == "greencloud-live":
        snap = collector.get_snapshot()
        spec = WorkloadSpec(
            name="greencloud-live",
            namespace="default",
            replicas=REPLICAS,
            cpu_request_m=CPU_REQUEST_M,
            cpu_limit_m=CPU_LIMIT_M,
            mem_request_mib=MEM_REQUEST_MIB,
            mem_limit_mib=MEM_LIMIT_MIB,
            is_simulated=False,
            description="Live Container/Host Environment"
        )
        metrics = ResourceMetrics(
            cpu_used_m=snap.cpu_used_m,
            cpu_peak_m=max(snap.cpu_peak_m, snap.cpu_used_m, 1.0),
            mem_used_mib=snap.mem_used_mib,
            mem_peak_mib=max(snap.mem_peak_mib, snap.mem_used_mib, 16.0),
            is_simulated=False
        )
    else:
        # Match demo workloads
        demos = {d["id"]: d for d in _get_demo_workloads()}
        if workload_id not in demos:
            return jsonify(error="Workload not found"), 404
        d = demos[workload_id]
        spec = WorkloadSpec(
            name=d["name"],
            namespace=d["namespace"],
            replicas=d["replicas"],
            cpu_request_m=d["cpu_request_m"],
            cpu_limit_m=d["cpu_limit_m"],
            mem_request_mib=d["mem_request_mib"],
            mem_limit_mib=d["mem_limit_mib"],
            is_simulated=True,
            description=d["description"]
        )
        metrics = ResourceMetrics(
            cpu_used_m=d["metrics"]["cpu_used_m"],
            cpu_peak_m=d["metrics"]["cpu_peak_m"],
            mem_used_mib=d["metrics"]["mem_used_mib"],
            mem_peak_mib=d["metrics"]["mem_peak_mib"],
            is_simulated=True
        )

    # Allow custom overrides from request if provided
    if "custom_spec" in data:
        cs = data["custom_spec"]
        spec.cpu_request_m = int(cs.get("cpu_request_m", spec.cpu_request_m))
        spec.mem_request_mib = int(cs.get("mem_request_mib", spec.mem_request_mib))
        spec.replicas = int(cs.get("replicas", spec.replicas))

    if "custom_metrics" in data:
        cm = data["custom_metrics"]
        metrics.cpu_used_m = float(cm.get("cpu_used_m", metrics.cpu_used_m))
        metrics.cpu_peak_m = float(cm.get("cpu_peak_m", metrics.cpu_peak_m))
        metrics.mem_used_mib = float(cm.get("mem_used_mib", metrics.mem_used_mib))
        metrics.mem_peak_mib = float(cm.get("mem_peak_mib", metrics.mem_peak_mib))

    audit = run_full_audit(spec, metrics, grid_region=grid_region, pue=pue)
    return jsonify(audit.to_dict())


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    """
    Simulation Laboratory Endpoint:
    Simulates a traffic spike on a workload and returns before-and-after analysis.
    Explicitly tags results as simulated.
    """
    data = request.get_json() or {}
    workload_id = data.get("workload_id", "auth-service")
    multiplier = max(0.2, min(10.0, float(data.get("traffic_multiplier", 2.0))))
    grid_region = data.get("grid_region", "global")
    pue = float(data.get("pue", PUE_PUBLIC_CLOUD))

    # Retrieve base workload
    if workload_id == "greencloud-live":
        snap = collector.get_snapshot()
        base_spec = WorkloadSpec(
            name="greencloud-live",
            namespace="default",
            replicas=REPLICAS,
            cpu_request_m=CPU_REQUEST_M,
            cpu_limit_m=CPU_LIMIT_M,
            mem_request_mib=MEM_REQUEST_MIB,
            mem_limit_mib=MEM_LIMIT_MIB,
            is_simulated=False
        )
        base_metrics = ResourceMetrics(
            cpu_used_m=snap.cpu_used_m,
            cpu_peak_m=max(snap.cpu_peak_m, snap.cpu_used_m, 1.0),
            mem_used_mib=snap.mem_used_mib,
            mem_peak_mib=max(snap.mem_peak_mib, snap.mem_used_mib, 16.0),
            is_simulated=False
        )
    else:
        demos = {d["id"]: d for d in _get_demo_workloads()}
        d = demos.get(workload_id, demos["auth-service"])
        base_spec = WorkloadSpec(
            name=d["name"],
            namespace=d["namespace"],
            replicas=d["replicas"],
            cpu_request_m=d["cpu_request_m"],
            cpu_limit_m=d["cpu_limit_m"],
            mem_request_mib=d["mem_request_mib"],
            mem_limit_mib=d["mem_limit_mib"],
            is_simulated=True
        )
        base_metrics = ResourceMetrics(
            cpu_used_m=d["metrics"]["cpu_used_m"],
            cpu_peak_m=d["metrics"]["cpu_peak_m"],
            mem_used_mib=d["metrics"]["mem_used_mib"],
            mem_peak_mib=d["metrics"]["mem_peak_mib"],
            is_simulated=True
        )

    # 1. Baseline audit
    baseline_audit = run_full_audit(base_spec, base_metrics, grid_region=grid_region, pue=pue)

    # 2. Simulated burst metrics
    sim_metrics = ResourceMetrics(
        cpu_used_m=round(base_metrics.cpu_used_m * multiplier, 2),
        cpu_peak_m=round(base_metrics.cpu_peak_m * multiplier, 2),
        mem_used_mib=round(min(base_spec.mem_limit_mib * 1.5, base_metrics.mem_used_mib * (1.0 + (multiplier - 1.0) * 0.4)), 2),
        mem_peak_mib=round(min(base_spec.mem_limit_mib * 1.8, base_metrics.mem_peak_mib * (1.0 + (multiplier - 1.0) * 0.5)), 2),
        is_simulated=True
    )

    burst_audit = run_full_audit(base_spec, sim_metrics, grid_region=grid_region, pue=pue)

    return jsonify(
        is_simulated=True,
        traffic_multiplier=multiplier,
        baseline_audit=baseline_audit.to_dict(),
        burst_audit=burst_audit.to_dict(),
        delta={
            "cpu_used_increase_m": round(sim_metrics.cpu_used_m - base_metrics.cpu_used_m, 2),
            "mem_used_increase_mib": round(sim_metrics.mem_used_mib - base_metrics.mem_used_mib, 2),
            "power_increase_watts": round(burst_audit.current_carbon.power_watts - baseline_audit.current_carbon.power_watts, 2),
            "carbon_increase_kg": round(burst_audit.current_carbon.monthly_carbon_kg - baseline_audit.current_carbon.monthly_carbon_kg, 2)
        }
    )


@app.route("/api/system-info")
def api_system_info():
    """Returns platform, host, and collector runtime diagnostics."""
    mem = psutil.virtual_memory()
    uptime_sec = time.time() - APP_START_TIME
    hours, remainder = divmod(int(uptime_sec), 3600)
    minutes, seconds = divmod(remainder, 60)

    snap = collector.get_snapshot()

    return jsonify(
        platform=platform.platform(),
        python_version=platform.python_version(),
        cpu_count_logical=psutil.cpu_count(logical=True),
        cpu_count_physical=psutil.cpu_count(logical=False),
        total_memory_gb=round(mem.total / (1024.0 ** 3), 2),
        available_memory_gb=round(mem.available / (1024.0 ** 3), 2),
        metric_source=snap.metric_source,
        is_container=snap.is_container,
        collector_running=collector.is_running(),
        collector_sample_count=snap.sample_count,
        uptime=f"{hours}h {minutes}m {seconds}s",
        uptime_seconds=round(uptime_sec, 1),
        cgroup_v2_exists=os.path.exists("/sys/fs/cgroup/cpu.stat"),
        cgroup_v1_exists=os.path.exists("/sys/fs/cgroup/cpu/cpuacct.usage"),
        regional_grid_options=list(REGIONAL_GRID_INTENSITY.keys())
    )


@app.route("/api/patch/<workload_id>")
def api_patch_download(workload_id):
    """Generates and downloads a Kubernetes optimization patch YAML file."""
    # Retrieve audit
    if workload_id == "greencloud-live":
        snap = collector.get_snapshot()
        spec = WorkloadSpec(name="greencloud-live", namespace="default", replicas=REPLICAS, cpu_request_m=CPU_REQUEST_M, cpu_limit_m=CPU_LIMIT_M, mem_request_mib=MEM_REQUEST_MIB, mem_limit_mib=MEM_LIMIT_MIB)
        metrics = ResourceMetrics(cpu_used_m=snap.cpu_used_m, cpu_peak_m=max(snap.cpu_peak_m, 1.0), mem_used_mib=snap.mem_used_mib, mem_peak_mib=max(snap.mem_peak_mib, 16.0))
    else:
        demos = {d["id"]: d for d in _get_demo_workloads()}
        d = demos.get(workload_id, demos["auth-service"])
        spec = WorkloadSpec(name=d["name"], namespace=d["namespace"], replicas=d["replicas"], cpu_request_m=d["cpu_request_m"], cpu_limit_m=d["cpu_limit_m"], mem_request_mib=d["mem_request_mib"], mem_limit_mib=d["mem_limit_mib"])
        metrics = ResourceMetrics(cpu_used_m=d["metrics"]["cpu_used_m"], cpu_peak_m=d["metrics"]["cpu_peak_m"], mem_used_mib=d["metrics"]["mem_used_mib"], mem_peak_mib=d["metrics"]["mem_peak_mib"])

    rec = analyze_and_recommend(spec, metrics)
    yaml_content = rec.k8s_patch_yaml

    return Response(
        yaml_content,
        mimetype="text/yaml",
        headers={"Content-Disposition": f"attachment; filename={workload_id}-optimization-patch.yaml"}
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
