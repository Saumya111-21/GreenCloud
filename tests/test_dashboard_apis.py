"""
Integration tests for Phase 3 Enterprise Dashboard APIs.
Validates HTML dashboard rendering, workload separation, auditing,
simulation laboratory, and Kubernetes patch generation.
"""

import json
import pytest
from app import app

@pytest.fixture
def client():
    """Flask test client fixture."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_dashboard_html_rendering(client):
    """Verify that GET / returns the full enterprise dashboard HTML."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode("utf-8")
    assert "GreenCloud" in html
    assert "Overview Dashboard" in html
    assert "Simulation Lab" in html
    assert "Intelligent Advisor" in html
    assert "Green Efficiency" in html


def test_api_workloads_separation(client):
    """Verify /api/workloads cleanly isolates LIVE workloads from DEMO workloads."""
    res = client.get("/api/workloads")
    assert res.status_code == 200
    data = res.get_json()

    assert "live_workload" in data
    assert "demo_workloads" in data
    assert data["total_count"] >= 4

    # Live workload must NOT be marked simulated
    assert data["live_workload"]["is_simulated"] is False
    assert data["live_workload"]["id"] == "greencloud-live"

    # All demo workloads MUST be marked simulated
    for dw in data["demo_workloads"]:
        assert dw["is_simulated"] is True


def test_api_audit_live_and_demo(client):
    """Verify POST /api/audit generates complete optimization and FinOps audits."""
    # 1. Audit Live Workload
    res_live = client.post(
        "/api/audit",
        data=json.dumps({"workload_id": "greencloud-live", "grid_region": "india"}),
        content_type="application/json"
    )
    assert res_live.status_code == 200
    audit_live = res_live.get_json()
    assert "recommendation" in audit_live
    assert "current_carbon" in audit_live
    assert "current_cost" in audit_live
    assert audit_live["recommendation"]["k8s_patch_yaml"].startswith("# GreenCloud Recommended Safe Optimization Patch")

    # 2. Audit Demo Workload
    res_demo = client.post(
        "/api/audit",
        data=json.dumps({"workload_id": "auth-service", "grid_region": "us_east"}),
        content_type="application/json"
    )
    assert res_demo.status_code == 200
    audit_demo = res_demo.get_json()
    assert audit_demo["recommendation"]["workload_name"] == "auth-service-prod"
    assert audit_demo["monthly_cost_saved_usd"] > 0


def test_api_simulate_traffic_spike(client):
    """Verify POST /api/simulate produces reactive before-and-after evaluations."""
    res = client.post(
        "/api/simulate",
        data=json.dumps({"workload_id": "auth-service", "traffic_multiplier": 3.0, "grid_region": "india"}),
        content_type="application/json"
    )
    assert res.status_code == 200
    sim = res.get_json()
    assert sim["is_simulated"] is True
    assert sim["traffic_multiplier"] == 3.0
    assert "baseline_audit" in sim
    assert "burst_audit" in sim
    assert "delta" in sim

    # Burst metrics must be strictly higher than baseline
    burst_cpu = sim["burst_audit"]["metrics"]["cpu_used_m"]
    base_cpu = sim["baseline_audit"]["metrics"]["cpu_used_m"]
    assert burst_cpu > base_cpu
    assert sim["delta"]["cpu_used_increase_m"] > 0


def test_api_system_info(client):
    """Verify GET /api/system-info returns diagnostic telemetry."""
    res = client.get("/api/system-info")
    assert res.status_code == 200
    info = res.get_json()
    assert "platform" in info
    assert "python_version" in info
    assert "cpu_count_logical" in info
    assert "total_memory_gb" in info
    assert "metric_source" in info
    assert "uptime" in info


def test_api_patch_download(client):
    """Verify GET /api/patch/<id> returns downloadable YAML file."""
    res = client.get("/api/patch/greencloud-live")
    assert res.status_code == 200
    assert res.mimetype == "text/yaml"
    yaml_text = res.data.decode("utf-8")
    assert "kind: Deployment" in yaml_text
    assert "name: greencloud-live" in yaml_text
