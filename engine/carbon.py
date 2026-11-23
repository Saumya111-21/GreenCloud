"""
Carbon and Sustainability Calculation Engine for GreenCloud.
Estimates power, energy consumption, and greenhouse gas (CO2e) emissions.
Methodology aligned with Cloud Carbon Footprint (CCF) and GHG Protocol Scope 2 standards.
"""

from .models import CarbonEstimate

# Regional average grid carbon intensities in gCO2e / kWh
# Sources: Ember Global Electricity Review, IEA, and Our World In Data
REGIONAL_GRID_INTENSITY = {
    "global": 440.0,       # Global average grid intensity
    "us_east": 379.0,      # US East (PJM / Virginia cloud corridor)
    "us_west": 215.0,      # US West (higher hydro and solar mix)
    "eu_central": 230.0,   # European Union average
    "eu_north": 45.0,      # Nordic regions (hydro/nuclear dominant)
    "india": 710.0,        # India national grid average (thermal dominant)
    "renewable": 15.0,     # Certified 100% renewable / wind / solar
    "green_100": 15.0,     # Alias for 100% green renewable power
}

# Industry standard server energy constants (SPECpower & Cloud Carbon Footprint)
PUE_PUBLIC_CLOUD = 1.20    # Hyperscale cloud average (Google, AWS, Azure)
PUE_PRIVATE_CLOUD = 1.50   # On-premise enterprise data center average

P_CPU_IDLE_WATTS = 0.75    # Base idle power per allocated vCPU core
P_CPU_MAX_WATTS = 3.50     # Peak power per allocated vCPU core under 100% load
P_RAM_WATTS_PER_GB = 0.38  # Power consumption per GB of active RAM

# EPA Greenhouse Gas Equivalencies
CO2_KG_PER_TREE_MONTH = 1.75    # 1 mature tree absorbs ~21 kg CO2/year (~1.75 kg/month)
CO2_KG_PER_CAR_MILE = 0.404     # Average passenger vehicle emits ~0.404 kg CO2 per mile


def calculate_power_watts(
    cpu_allocated_m: int,
    cpu_used_m: float,
    mem_allocated_mib: int,
    pue: float = PUE_PUBLIC_CLOUD,
    replicas: int = 1
) -> float:
    """
    Calculates instantaneous power draw in Watts for a given workload.
    Formula: Total Power = (P_cpu + P_ram) * PUE * replicas
    """
    cores = max(0.01, cpu_allocated_m / 1000.0)
    ram_gb = max(0.032, mem_allocated_mib / 1024.0)
    
    # Calculate CPU utilization ratio between 0.0 and 1.0
    utilization_ratio = max(0.0, min(1.0, cpu_used_m / max(1.0, float(cpu_allocated_m))))
    
    # Linear dynamic power curve between idle and max
    p_cpu_single_core = P_CPU_IDLE_WATTS + utilization_ratio * (P_CPU_MAX_WATTS - P_CPU_IDLE_WATTS)
    p_cpu_total = cores * p_cpu_single_core
    
    # RAM power
    p_ram_total = ram_gb * P_RAM_WATTS_PER_GB
    
    total_power = (p_cpu_total + p_ram_total) * pue * replicas
    return round(total_power, 4)


def estimate_carbon_footprint(
    cpu_allocated_m: int,
    cpu_used_m: float,
    mem_allocated_mib: int,
    replicas: int = 1,
    grid_region: str = "global",
    pue: float = PUE_PUBLIC_CLOUD,
    hours_per_month: float = 730.0
) -> CarbonEstimate:
    """
    Generates a full carbon footprint estimate for monthly operation.
    """
    region_key = grid_region.lower()
    intensity = REGIONAL_GRID_INTENSITY.get(region_key, REGIONAL_GRID_INTENSITY["global"])
    
    power_watts = calculate_power_watts(
        cpu_allocated_m=cpu_allocated_m,
        cpu_used_m=cpu_used_m,
        mem_allocated_mib=mem_allocated_mib,
        pue=pue,
        replicas=replicas
    )
    
    # Monthly Energy in kWh = (Watts * hours) / 1000
    monthly_kwh = (power_watts * hours_per_month) / 1000.0
    
    # Monthly Carbon in kg CO2e = (kWh * gCO2e/kWh) / 1000
    monthly_co2_kg = (monthly_kwh * intensity) / 1000.0
    
    # Real-world impact equivalents
    trees_needed = monthly_co2_kg / CO2_KG_PER_TREE_MONTH if CO2_KG_PER_TREE_MONTH > 0 else 0.0
    car_miles = monthly_co2_kg / CO2_KG_PER_CAR_MILE if CO2_KG_PER_CAR_MILE > 0 else 0.0
    
    return CarbonEstimate(
        power_watts=round(power_watts, 2),
        monthly_energy_kwh=round(monthly_kwh, 2),
        monthly_carbon_kg=round(monthly_co2_kg, 2),
        carbon_intensity_g_per_kwh=intensity,
        grid_region=grid_region,
        pue=pue,
        trees_offset_equivalent=round(trees_needed, 1),
        car_miles_equivalent=round(car_miles, 1),
        is_estimate=True,
        methodology="SPECpower / Cloud Carbon Footprint (CCF) Scope 2"
    )
