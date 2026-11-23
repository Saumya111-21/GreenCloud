"""Unit tests for the Intelligent Advisor and Right-Sizing Engine."""

from engine.models import WorkloadSpec, ResourceMetrics
from engine.advisor import analyze_and_recommend, advise

def test_legacy_advise_backward_compatibility():
    """Verify legacy advise() signature works identically to previous version."""
    util, tips = advise(pod_count=2, cpu_used_m=0.25, cpu_request_m=100, peak_used_m=2.0)
    assert round(util, 2) == 0.25
    assert len(tips) > 0
    assert any("Over-provisioned" in t for t in tips)

def test_zero_division_protection():
    """Verify that 0 CPU request or 0 Memory request does not crash with ZeroDivisionError."""
    spec = WorkloadSpec(name="zero-test", replicas=1, cpu_request_m=0, cpu_limit_m=0, mem_request_mib=0, mem_limit_mib=0)
    metrics = ResourceMetrics(cpu_used_m=5.0, cpu_peak_m=10.0, mem_used_mib=20.0, mem_peak_mib=30.0)
    rec = analyze_and_recommend(spec, metrics)
    assert rec.cpu_utilization_pct == 0.0
    assert rec.mem_utilization_pct == 0.0
    assert rec.recommended_cpu_request_m >= 10
    assert rec.recommended_mem_request_mib >= 32

def test_overprovisioned_workload_recommendation():
    """Verify right-sizing on a heavily over-provisioned workload."""
    spec = WorkloadSpec(
        name="web-frontend",
        replicas=2,
        cpu_request_m=100,
        cpu_limit_m=250,
        mem_request_mib=256,
        mem_limit_mib=512
    )
    metrics = ResourceMetrics(
        cpu_used_m=1.0,
        cpu_peak_m=4.0,
        mem_used_mib=40.0,
        mem_peak_mib=60.0
    )
    rec = analyze_and_recommend(spec, metrics, safety_margin_cpu=0.25, safety_margin_mem=0.30)
    
    # Peak CPU is 4.0m with 25% safety margin -> 4 * 1.25 = 5m -> capped by min_cpu_m (10m)
    assert rec.recommended_cpu_request_m == 10
    assert rec.cpu_request_delta_m == 90
    assert rec.cpu_request_reduction_pct == 90.0
    assert rec.status == "CRITICAL_OVERPROVISIONED"
    assert rec.risk_level == "SAFE"
    assert "Deployment" in rec.k8s_patch_yaml
    assert "cpu: \"10m\"" in rec.k8s_patch_yaml

def test_underprovisioned_workload_protection():
    """Verify that overloaded workloads receive urgent upscaling recommendations."""
    spec = WorkloadSpec(
        name="database-worker",
        replicas=1,
        cpu_request_m=50,
        cpu_limit_m=100,
        mem_request_mib=128,
        mem_limit_mib=256
    )
    metrics = ResourceMetrics(
        cpu_used_m=48.0,
        cpu_peak_m=95.0,
        mem_used_mib=120.0,
        mem_peak_mib=240.0
    )
    rec = analyze_and_recommend(spec, metrics)
    assert rec.status == "CRITICAL_UNDERPROVISIONED"
    assert rec.risk_level == "HIGH"
    assert rec.recommended_cpu_request_m > spec.cpu_request_m
    assert rec.recommended_mem_request_mib > spec.mem_request_mib
    assert any("raise CPU request" in t for t in rec.tips)

def test_healthy_optimal_workload():
    """Verify that workloads running at 50% utilization are flagged as OPTIMAL and remain unchanged."""
    spec = WorkloadSpec(
        name="api-gateway",
        replicas=2,
        cpu_request_m=100,
        cpu_limit_m=200,
        mem_request_mib=256,
        mem_limit_mib=512
    )
    metrics = ResourceMetrics(
        cpu_used_m=50.0,
        cpu_peak_m=65.0,
        mem_used_mib=128.0,
        mem_peak_mib=160.0
    )
    rec = analyze_and_recommend(spec, metrics)
    assert rec.status == "OPTIMAL"
    assert rec.risk_level == "SAFE"
    assert rec.action_required is False
    assert rec.recommended_cpu_request_m == spec.cpu_request_m
    assert rec.recommended_mem_request_mib == spec.mem_request_mib
    assert rec.cpu_request_delta_m == 0
