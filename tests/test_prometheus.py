"""
Unit and integration tests for Prometheus exposition format and Kubernetes hardening.
Validates Prometheus syntax, scrape compliance, K8s manifests, probes, and securityContext.
"""

from pathlib import Path
import yaml
import pytest

from engine.collector import CollectorSnapshot
from engine.models import WorkloadSpec, ResourceMetrics
from engine.advisor import run_full_audit
from engine.prometheus import (
    format_prometheus_metrics,
    parse_and_validate_prometheus_text,
    PROMETHEUS_CONTENT_TYPE,
)
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_prometheus_formatting_and_validation():
    """Verify Prometheus text format meets standard exposition syntax specifications."""
    snapshot = CollectorSnapshot(
        timestamp=1700000000.0,
        cpu_percent=15.5,
        cpu_used_m=31.0,
        cpu_peak_m=50.0,
        mem_used_mib=64.0,
        mem_peak_mib=80.0,
        mem_percent=50.0,
        metric_source="host_system",
        is_container=False,
        sample_count=100
    )
    spec = WorkloadSpec(name="greencloud-test", replicas=2, cpu_request_m=100, cpu_limit_m=200, mem_request_mib=128, mem_limit_mib=256)
    metrics = ResourceMetrics(cpu_used_m=31.0, cpu_peak_m=50.0, mem_used_mib=64.0, mem_peak_mib=80.0)
    audit = run_full_audit(spec, metrics, grid_region="india")

    prom_text = format_prometheus_metrics(snapshot, audit)
    assert isinstance(prom_text, str)
    assert prom_text.endswith("\n")

    # Validate syntax structure
    validation = parse_and_validate_prometheus_text(prom_text)
    assert validation["valid"] is True
    assert validation["metric_count"] >= 10
    assert "greencloud_up" in validation["metrics"]
    assert "greencloud_cpu_used_millicores" in validation["metrics"]
    assert "greencloud_power_consumption_watts" in validation["metrics"]
    assert "greencloud_monthly_carbon_emissions_kg" in validation["metrics"]
    assert "greencloud_monthly_cost_usd" in validation["metrics"]


def test_prometheus_scrape_endpoint(client):
    """Verify that Prometheus scrapers receive valid text/plain metrics from /metrics."""
    res = client.get("/metrics", headers={"Accept": "text/plain;version=0.0.4"})
    assert res.status_code == 200
    assert PROMETHEUS_CONTENT_TYPE in res.content_type
    
    text = res.data.decode("utf-8")
    validation = parse_and_validate_prometheus_text(text)
    assert validation["valid"] is True
    assert validation["metrics"]["greencloud_up"] == 1.0


def test_kubernetes_deployment_hardening():
    """Verify deployment.yaml includes health probes, securityContext, and Prometheus annotations."""
    dep_path = Path("deployment.yaml")
    assert dep_path.exists()

    with open(dep_path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    assert doc["kind"] == "Deployment"
    spec = doc["spec"]["template"]["spec"]

    # 1. Prometheus Scrape Annotations
    annotations = doc["spec"]["template"]["metadata"]["annotations"]
    assert annotations["prometheus.io/scrape"] == "true"
    assert annotations["prometheus.io/port"] == "5000"
    assert annotations["prometheus.io/path"] == "/metrics"

    # 2. SecurityContext (Pod Level)
    assert spec["securityContext"]["runAsNonRoot"] is True
    assert spec["securityContext"]["runAsUser"] == 10001

    # 3. Container Specs & Probes
    container = spec["containers"][0]
    assert "livenessProbe" in container
    assert container["livenessProbe"]["httpGet"]["path"] == "/api/snapshot"
    assert "readinessProbe" in container
    assert container["readinessProbe"]["httpGet"]["path"] == "/api/snapshot"

    # 4. Container Level SecurityContext
    assert container["securityContext"]["allowPrivilegeEscalation"] is False
    assert "ALL" in container["securityContext"]["capabilities"]["drop"]

    # 5. Resources configured
    assert container["resources"]["requests"]["cpu"] == "10m"
    assert container["resources"]["requests"]["memory"] == "64Mi"


def test_kubernetes_service_annotations():
    """Verify service.yaml contains Prometheus scrape annotations."""
    svc_path = Path("service.yaml")
    assert svc_path.exists()

    with open(svc_path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    assert doc["kind"] == "Service"
    assert doc["metadata"]["annotations"]["prometheus.io/scrape"] == "true"


def test_kubernetes_hpa_manifest():
    """Verify kubernetes/hpa.yaml contains valid HorizontalPodAutoscaler spec."""
    hpa_path = Path("kubernetes/hpa.yaml")
    assert hpa_path.exists()

    with open(hpa_path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    assert doc["kind"] == "HorizontalPodAutoscaler"
    assert doc["spec"]["scaleTargetRef"]["name"] == "greencloud"
    assert doc["spec"]["minReplicas"] == 2
    assert doc["spec"]["maxReplicas"] == 5


def test_dockerfile_hardening():
    """Verify Dockerfile enforces non-root user and HEALTHCHECK."""
    dockerfile_path = Path("Dockerfile")
    assert dockerfile_path.exists()
    content = dockerfile_path.read_text(encoding="utf-8")

    assert "USER 10001" in content or "USER appuser" in content
    assert "HEALTHCHECK" in content
    assert "COPY engine/" in content
    assert "COPY templates/" in content
    assert "COPY static/" in content
