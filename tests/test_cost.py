"""Unit tests for Cloud Cost Estimation (FinOps)."""

from engine.cost import estimate_cloud_cost, PRICE_PER_VCPU_HOUR, PRICE_PER_GB_HOUR

def test_cloud_cost_calculation():
    """Verify monthly cost matches standard cloud benchmark formulas."""
    cost = estimate_cloud_cost(cpu_request_m=1000, mem_request_mib=1024, replicas=1)
    expected_hourly = PRICE_PER_VCPU_HOUR + PRICE_PER_GB_HOUR
    expected_monthly = expected_hourly * 730.0
    
    assert round(cost.hourly_cost_usd, 4) == round(expected_hourly, 4)
    assert round(cost.monthly_cost_usd, 2) == round(expected_monthly, 2)
    assert cost.is_estimate is True

def test_multi_replica_cost():
    """Verify that multi-replica costs scale linearly."""
    c1 = estimate_cloud_cost(cpu_request_m=500, mem_request_mib=512, replicas=1)
    c3 = estimate_cloud_cost(cpu_request_m=500, mem_request_mib=512, replicas=3)
    assert round(c3.monthly_cost_usd, 2) == round(c1.monthly_cost_usd * 3, 2)
