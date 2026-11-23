"""Unit tests for the Carbon Footprint and Sustainability Engine."""

from engine.carbon import (
    calculate_power_watts,
    estimate_carbon_footprint,
    PUE_PUBLIC_CLOUD,
    PUE_PRIVATE_CLOUD,
)

def test_calculate_power_watts_scaling():
    """Verify power increases logically with CPU utilization and replicas."""
    idle_watts = calculate_power_watts(cpu_allocated_m=1000, cpu_used_m=0.0, mem_allocated_mib=1024, replicas=1)
    loaded_watts = calculate_power_watts(cpu_allocated_m=1000, cpu_used_m=1000.0, mem_allocated_mib=1024, replicas=1)
    assert loaded_watts > idle_watts

    replica2_watts = calculate_power_watts(cpu_allocated_m=1000, cpu_used_m=500.0, mem_allocated_mib=1024, replicas=2)
    replica1_watts = calculate_power_watts(cpu_allocated_m=1000, cpu_used_m=500.0, mem_allocated_mib=1024, replicas=1)
    assert round(replica2_watts, 2) == round(replica1_watts * 2, 2)

def test_regional_carbon_intensities():
    """Verify that dirtier grids (e.g. coal-heavy) compute higher carbon emissions."""
    green_est = estimate_carbon_footprint(cpu_allocated_m=500, cpu_used_m=50, mem_allocated_mib=512, grid_region="green_100")
    india_est = estimate_carbon_footprint(cpu_allocated_m=500, cpu_used_m=50, mem_allocated_mib=512, grid_region="india")
    us_est = estimate_carbon_footprint(cpu_allocated_m=500, cpu_used_m=50, mem_allocated_mib=512, grid_region="us_east")

    assert green_est.monthly_carbon_kg < us_est.monthly_carbon_kg < india_est.monthly_carbon_kg
    assert green_est.is_estimate is True
    assert green_est.trees_offset_equivalent >= 0.0
    assert green_est.car_miles_equivalent >= 0.0

def test_pue_impact():
    """Verify higher PUE (e.g. private on-premise DC) reflects higher power overhead."""
    public_est = estimate_carbon_footprint(cpu_allocated_m=1000, cpu_used_m=500, mem_allocated_mib=1024, pue=PUE_PUBLIC_CLOUD)
    private_est = estimate_carbon_footprint(cpu_allocated_m=1000, cpu_used_m=500, mem_allocated_mib=1024, pue=PUE_PRIVATE_CLOUD)
    assert private_est.power_watts > public_est.power_watts
