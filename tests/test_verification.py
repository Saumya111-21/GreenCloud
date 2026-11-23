"""
Comprehensive Phase 1 Verification Test Suite.
Validates CPU/Memory right-sizing, division-by-zero safety, carbon estimation,
cloud cost estimation, and backward compatibility.
"""

from engine.models import WorkloadSpec, ResourceMetrics
from engine.advisor import analyze_and_recommend, advise, run_full_audit
from engine.carbon import (
    calculate_power_watts,
    estimate_carbon_footprint,
    REGIONAL_GRID_INTENSITY,
    PUE_PUBLIC_CLOUD,
)
from engine.cost import estimate_cloud_cost, PRICE_PER_VCPU_HOUR, PRICE_PER_GB_HOUR

def test_cpu_optimization_right_sizing():
    """Verify CPU optimization math with safety buffer."""
    spec = WorkloadSpec(name="cpu-test", replicas=1, cpu_request_m=200, cpu_limit_m=400, mem_request_mib=128, mem_limit_mib=256)
    # Peak is 20m. Safety margin 25% -> 20 * 1.25 = 25m.
    metrics = ResourceMetrics(cpu_used_m=5.0, cpu_peak_m=20.0, mem_used_mib=32.0, mem_peak_mib=40.0)
    rec = analyze_and_recommend(spec, metrics, safety_margin_cpu=0.25)
    assert rec.recommended_cpu_request_m == 25
    assert rec.cpu_request_delta_m == 175
    assert rec.cpu_request_reduction_pct == 87.5

def test_memory_optimization_right_sizing():
    """Verify Memory optimization math with safety buffer."""
    spec = WorkloadSpec(name="mem-test", replicas=1, cpu_request_m=100, cpu_limit_m=200, mem_request_mib=512, mem_limit_mib=1024)
    # Peak memory is 100 MiB. Safety margin 30% -> 100 * 1.30 = 130 MiB.
    metrics = ResourceMetrics(cpu_used_m=10.0, cpu_peak_m=20.0, mem_used_mib=80.0, mem_peak_mib=100.0)
    rec = analyze_and_recommend(spec, metrics, safety_margin_mem=0.30)
    assert rec.recommended_mem_request_mib == 130
    assert rec.mem_request_delta_mib == 382
    # Recommended limit should be at least request + 32 and peak * 1.5
    assert rec.recommended_mem_limit_mib >= rec.recommended_mem_request_mib + 32
    assert rec.recommended_mem_limit_mib >= 150

def test_division_by_zero_all_fields():
    """Verify zero inputs in requests and metrics do not cause runtime crashes."""
    spec = WorkloadSpec(name="zero-spec", replicas=0, cpu_request_m=0, cpu_limit_m=0, mem_request_mib=0, mem_limit_mib=0)
    metrics = ResourceMetrics(cpu_used_m=0.0, cpu_peak_m=0.0, mem_used_mib=0.0, mem_peak_mib=0.0)
    rec = analyze_and_recommend(spec, metrics)
    assert rec.cpu_utilization_pct == 0.0
    assert rec.mem_utilization_pct == 0.0
    assert rec.recommended_cpu_request_m >= 10
    assert rec.recommended_mem_request_mib >= 32

    # Verify zero in cost and carbon
    cost = estimate_cloud_cost(cpu_request_m=0, mem_request_mib=0, replicas=0)
    assert cost.monthly_cost_usd == 0.0
    power = calculate_power_watts(cpu_allocated_m=0, cpu_used_m=0, mem_allocated_mib=0, replicas=0)
    assert power == 0.0

def test_carbon_calculations_sample_inputs():
    """Verify carbon calculations with documented sample inputs."""
    # 1 vCPU (1000m), 100% load (1000m used), 1 GiB RAM (1024MiB), 1 replica, PUE 1.2
    # P_cpu = 1 * (0.75 + 1.0 * (3.5 - 0.75)) = 3.50 W
    # P_ram = 1 * 0.38 = 0.38 W
    # Total power = (3.50 + 0.38) * 1.2 = 3.88 * 1.2 = 4.656 W
    watts = calculate_power_watts(cpu_allocated_m=1000, cpu_used_m=1000.0, mem_allocated_mib=1024, pue=1.2, replicas=1)
    assert round(watts, 2) == 4.66

    # Monthly energy = 4.656 * 730 / 1000 = 3.39888 kWh (~3.40 kWh)
    # India grid (710 g/kWh) -> 3.39888 * 710 / 1000 = 2.413 kg CO2e (~2.41 kg)
    est = estimate_carbon_footprint(cpu_allocated_m=1000, cpu_used_m=1000.0, mem_allocated_mib=1024, replicas=1, grid_region="india", pue=1.2)
    assert round(est.monthly_energy_kwh, 2) == 3.40
    assert round(est.monthly_carbon_kg, 2) == 2.41
    assert est.is_estimate is True

def test_cost_estimation_sample_inputs():
    """Verify cloud cost calculations with exact sample rates."""
    # 2 vCPUs (2000m) and 4 GiB (4096 MiB) with 2 replicas
    # Hourly = (2 * 0.0310 + 4 * 0.0041) * 2 = (0.0620 + 0.0164) * 2 = 0.0784 * 2 = $0.1568/hr
    # Monthly = 0.1568 * 730 = $114.464 (~$114.46)
    cost = estimate_cloud_cost(cpu_request_m=2000, mem_request_mib=4096, replicas=2)
    assert round(cost.hourly_cost_usd, 4) == 0.1568
    assert round(cost.monthly_cost_usd, 2) == 114.46
    assert cost.is_estimate is True

def test_original_app_compatibility():
    """Verify existing legacy imports and app.py functions without any regression."""
    # Test legacy advise
    util, tips = advise(pod_count=2, cpu_used_m=0.25, cpu_request_m=100, peak_used_m=2)
    assert round(util, 2) == 0.25
    assert len(tips) > 0

    # Test importing app without side-effects
    import app
    assert hasattr(app, "app")
    assert hasattr(app, "get_advice")
    assert hasattr(app, "metrics")

def test_full_audit_consistency():
    """Verify FullOptimizationAudit ties recommendations, cost, and carbon together consistently."""
    spec = WorkloadSpec(name="audit-pod", replicas=2, cpu_request_m=100, cpu_limit_m=200, mem_request_mib=64, mem_limit_mib=128)
    metrics = ResourceMetrics(cpu_used_m=1.0, cpu_peak_m=2.0, mem_used_mib=30.0, mem_peak_mib=40.0)
    audit = run_full_audit(spec, metrics, grid_region="us_east")

    assert audit.monthly_cost_saved_usd > 0
    assert audit.cost_savings_pct > 0
    assert audit.monthly_carbon_saved_kg > 0
    assert audit.carbon_savings_pct > 0
    assert "Deployment" in audit.recommendation.k8s_patch_yaml
    assert audit.recommendation.k8s_patch_yaml.startswith("# GreenCloud Recommended Safe Optimization Patch")
