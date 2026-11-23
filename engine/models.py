"""
Data models for GreenCloud resource monitoring, optimization, and sustainability.
"""

from dataclasses import dataclass, field, asdict
from typing import List
import time

@dataclass
class WorkloadSpec:
    """Represents a Kubernetes deployment or container workload specification."""
    name: str
    namespace: str = "default"
    replicas: int = 1
    cpu_request_m: int = 100       # millicores (1000m = 1 vCPU)
    cpu_limit_m: int = 200         # millicores
    mem_request_mib: int = 128     # MiB
    mem_limit_mib: int = 256       # MiB
    is_simulated: bool = False     # Explicitly flags if workload is simulated for demo
    description: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class ResourceMetrics:
    """Historical or instantaneous measurements of a workload's consumption."""
    cpu_used_m: float              # current or average CPU used in millicores
    cpu_peak_m: float              # measured peak CPU used in millicores
    mem_used_mib: float            # current or average memory used in MiB
    mem_peak_mib: float            # measured peak memory used in MiB
    timestamp: float = field(default_factory=time.time)
    sample_count: int = 1
    is_simulated: bool = False     # Explicitly flags simulated vs real metrics

    def to_dict(self):
        return asdict(self)


@dataclass
class RightSizingRecommendation:
    """Recommended resource allocations with safety buffers and justification."""
    workload_name: str
    namespace: str

    # Current specifications
    current_replicas: int
    current_cpu_request_m: int
    current_cpu_limit_m: int
    current_mem_request_mib: int
    current_mem_limit_mib: int

    # Measured utilization percentages
    cpu_utilization_pct: float
    mem_utilization_pct: float

    # Recommended specifications
    recommended_replicas: int
    recommended_cpu_request_m: int
    recommended_cpu_limit_m: int
    recommended_mem_request_mib: int
    recommended_mem_limit_mib: int

    # Savings & changes
    cpu_request_delta_m: int
    cpu_request_reduction_pct: float
    mem_request_delta_mib: int
    mem_request_reduction_pct: float

    # Status classification
    status: str                    # CRITICAL_OVERPROVISIONED, OVERPROVISIONED, OPTIMAL, UNDERPROVISIONED_WARNING, CRITICAL_UNDERPROVISIONED
    risk_level: str                # SAFE, MODERATE, HIGH
    action_required: bool
    summary: str
    tips: List[str]

    # Safe optimization: YAML patch for administrator inspection and manual approval
    k8s_patch_yaml: str

    def to_dict(self):
        return asdict(self)


@dataclass
class CarbonEstimate:
    """
    Sustainability and carbon footprint estimate.
    Follows Cloud Carbon Footprint (CCF) & GHG Protocol scope 2 methodology.
    """
    power_watts: float             # Total instantaneous power draw in Watts
    monthly_energy_kwh: float      # Projected monthly energy consumption in kWh
    monthly_carbon_kg: float       # Projected monthly CO2e emissions in kg
    carbon_intensity_g_per_kwh: float # Regional grid emission factor in gCO2e/kWh
    grid_region: str               # e.g., 'US-East', 'EU-Central', 'India', 'Global'
    pue: float                     # Data center Power Usage Effectiveness
    trees_offset_equivalent: float # Number of mature trees required for annual offset
    car_miles_equivalent: float    # Equivalent passenger car miles driven
    is_estimate: bool = True       # Always explicitly labeled as an estimate
    methodology: str = "SPECpower / Cloud Carbon Footprint (CCF) Scope 2"

    def to_dict(self):
        return asdict(self)


@dataclass
class CostEstimate:
    """
    Cloud financial management (FinOps) estimate.
    Based on standard general-purpose public cloud on-demand pricing benchmarks.
    """
    monthly_cost_usd: float        # Projected monthly cost in USD
    hourly_cost_usd: float         # Projected hourly cost in USD
    cpu_monthly_usd: float         # Breakdown: monthly CPU cost
    mem_monthly_usd: float         # Breakdown: monthly RAM cost
    pricing_model: str             # e.g., 'General Purpose On-Demand (AWS t3/m5 / GCP e2)'
    is_estimate: bool = True       # Always explicitly labeled as an estimate

    def to_dict(self):
        return asdict(self)


@dataclass
class FullOptimizationAudit:
    """Complete workload audit combining right-sizing, sustainability, and FinOps."""
    spec: WorkloadSpec
    metrics: ResourceMetrics
    recommendation: RightSizingRecommendation
    current_carbon: CarbonEstimate
    optimized_carbon: CarbonEstimate
    current_cost: CostEstimate
    optimized_cost: CostEstimate
    monthly_cost_saved_usd: float
    cost_savings_pct: float
    monthly_carbon_saved_kg: float
    carbon_savings_pct: float

    def to_dict(self):
        return {
            "spec": self.spec.to_dict(),
            "metrics": self.metrics.to_dict(),
            "recommendation": self.recommendation.to_dict(),
            "current_carbon": self.current_carbon.to_dict(),
            "optimized_carbon": self.optimized_carbon.to_dict(),
            "current_cost": self.current_cost.to_dict(),
            "optimized_cost": self.optimized_cost.to_dict(),
            "monthly_cost_saved_usd": round(self.monthly_cost_saved_usd, 2),
            "cost_savings_pct": round(self.cost_savings_pct, 1),
            "monthly_carbon_saved_kg": round(self.monthly_carbon_saved_kg, 2),
            "carbon_savings_pct": round(self.carbon_savings_pct, 1),
        }
