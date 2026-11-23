"""
Cloud Cost Estimation Engine for GreenCloud (FinOps).
Estimates hourly and monthly infrastructure costs based on standard public cloud benchmarks.
"""

from .models import CostEstimate

# Benchmark public cloud on-demand hourly pricing (General Purpose equivalent, e.g., AWS t3/m5 or GCP e2)
# Prices in USD
PRICE_PER_VCPU_HOUR = 0.0310   # ~$0.031 per vCPU hour ($0.000031 per millicore-hour)
PRICE_PER_GB_HOUR = 0.0041     # ~$0.0041 per GiB hour ($0.0000040039 per MiB-hour)
HOURS_PER_MONTH = 730.0        # Average hours in a calendar month


def estimate_cloud_cost(
    cpu_request_m: int,
    mem_request_mib: int,
    replicas: int = 1,
    pricing_model: str = "Standard Cloud General-Purpose"
) -> CostEstimate:
    """
    Calculates estimated hourly and monthly cost for cloud resource reservations.
    In cloud environments (Kubernetes nodes or serverless containers like ECS/Fargate),
    tenants are billed for requested capacity.
    """
    cores = max(0.0, cpu_request_m / 1000.0)
    ram_gb = max(0.0, mem_request_mib / 1024.0)
    
    hourly_cpu = cores * PRICE_PER_VCPU_HOUR * replicas
    hourly_mem = ram_gb * PRICE_PER_GB_HOUR * replicas
    hourly_total = hourly_cpu + hourly_mem
    
    monthly_cpu = hourly_cpu * HOURS_PER_MONTH
    monthly_mem = hourly_mem * HOURS_PER_MONTH
    monthly_total = hourly_total * HOURS_PER_MONTH
    
    return CostEstimate(
        monthly_cost_usd=round(monthly_total, 2),
        hourly_cost_usd=round(hourly_total, 4),
        cpu_monthly_usd=round(monthly_cpu, 2),
        mem_monthly_usd=round(monthly_mem, 2),
        pricing_model=pricing_model,
        is_estimate=True
    )
