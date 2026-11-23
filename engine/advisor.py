"""
Intelligent Resource Right-Sizing and Optimization Engine for GreenCloud.
Analyzes CPU and memory utilization, enforces safety buffers, and generates non-destructive recommendations.
"""

import math
from typing import List, Tuple
from .models import (
    WorkloadSpec,
    ResourceMetrics,
    RightSizingRecommendation,
    FullOptimizationAudit,
)
from .carbon import estimate_carbon_footprint, PUE_PUBLIC_CLOUD
from .cost import estimate_cloud_cost


def analyze_and_recommend(
    spec: WorkloadSpec,
    metrics: ResourceMetrics,
    safety_margin_cpu: float = 0.25,    # 25% safety headroom above measured peak
    safety_margin_mem: float = 0.30,    # 30% safety headroom above measured peak (prevents OOMKill)
    min_cpu_m: int = 10,                # 10 millicores minimum floor
    min_mem_mib: int = 32,              # 32 MiB minimum floor
    downscale_replica_threshold_pct: float = 10.0
) -> RightSizingRecommendation:
    """
    Performs intelligent right-sizing analysis on a workload.
    Guarantees no division by zero and provides safe, actionable suggestions.
    """
    # Safe utilization calculation (prevents ZeroDivisionError)
    cpu_util = (metrics.cpu_used_m / spec.cpu_request_m * 100.0) if spec.cpu_request_m > 0 else 0.0
    mem_util = (metrics.mem_used_mib / spec.mem_request_mib * 100.0) if spec.mem_request_mib > 0 else 0.0

    tips: List[str] = []
    
    # Calculate baseline peak usage
    effective_peak_cpu = max(metrics.cpu_peak_m, metrics.cpu_used_m, 1.0)
    effective_peak_mem = max(metrics.mem_peak_mib, metrics.mem_used_mib, 16.0)

    recommended_replicas = spec.replicas

    # Classify optimization state and determine recommendations
    if cpu_util < 10.0 or mem_util < 15.0:
        status = "CRITICAL_OVERPROVISIONED"
        risk_level = "SAFE"
        action_required = True
        summary = "Substantial waste detected. Severe over-provisioning can be right-sized safely."
        
        # Right-size down safely with safety margin
        recommended_cpu_request_m = max(min_cpu_m, math.ceil(effective_peak_cpu * (1.0 + safety_margin_cpu)))
        recommended_cpu_limit_m = max(recommended_cpu_request_m * 2, math.ceil(effective_peak_cpu * 2.5), 20)
        recommended_mem_request_mib = max(min_mem_mib, math.ceil(effective_peak_mem * (1.0 + safety_margin_mem)))
        recommended_mem_limit_mib = max(recommended_mem_request_mib + 32, math.ceil(effective_peak_mem * 1.5), 64)

        tips.append(
            f"Over-provisioned: CPU request can safely decrease from {spec.cpu_request_m}m to {recommended_cpu_request_m}m "
            f"({math.floor((1 - recommended_cpu_request_m / max(1, spec.cpu_request_m)) * 100)}% reduction)."
        )
        if spec.mem_request_mib > recommended_mem_request_mib:
            tips.append(
                f"Memory over-provisioned: request can decrease from {spec.mem_request_mib}Mi to {recommended_mem_request_mib}Mi."
            )
        # Check replica reduction for non-HA
        if spec.replicas > 1 and cpu_util < downscale_replica_threshold_pct and mem_util < 25.0:
            combined_peak = effective_peak_cpu * spec.replicas
            if combined_peak < spec.cpu_request_m * 0.7:
                recommended_replicas = max(1, spec.replicas - 1)
                tips.append(
                    f"Workload is severely underutilized ({cpu_util:.1f}% CPU). "
                    f"Consider scaling replicas from {spec.replicas} to {recommended_replicas} if High Availability is optional."
                )

    elif cpu_util < 25.0 or mem_util < 30.0:
        status = "OVERPROVISIONED"
        risk_level = "SAFE"
        action_required = True
        summary = "Moderate over-provisioning detected. Optimization will lower costs and carbon footprint."
        
        recommended_cpu_request_m = max(min_cpu_m, math.ceil(effective_peak_cpu * (1.0 + safety_margin_cpu)))
        recommended_cpu_limit_m = max(recommended_cpu_request_m * 2, math.ceil(effective_peak_cpu * 2.5), 20)
        recommended_mem_request_mib = max(min_mem_mib, math.ceil(effective_peak_mem * (1.0 + safety_margin_mem)))
        recommended_mem_limit_mib = max(recommended_mem_request_mib + 32, math.ceil(effective_peak_mem * 1.5), 64)

        tips.append(
            f"Moderate waste: lower CPU request to {recommended_cpu_request_m}m and memory to {recommended_mem_request_mib}Mi."
        )

    elif cpu_util > 85.0 or mem_util > 85.0:
        status = "CRITICAL_UNDERPROVISIONED"
        risk_level = "HIGH"
        action_required = True
        summary = "Workload under severe pressure! Throttling or Out-Of-Memory (OOMKill) risk detected."
        
        # Upscale to prevent throttling/crashes
        recommended_cpu_request_m = max(spec.cpu_request_m, math.ceil(effective_peak_cpu * 1.5))
        recommended_cpu_limit_m = max(spec.cpu_limit_m, math.ceil(effective_peak_cpu * 2.0))
        recommended_mem_request_mib = max(spec.mem_request_mib, math.ceil(effective_peak_mem * 1.4))
        recommended_mem_limit_mib = max(spec.mem_limit_mib, math.ceil(effective_peak_mem * 1.8))
        
        tips.append(
            f"Under-provisioned: raise CPU request to at least {recommended_cpu_request_m}m "
            f"and memory to {recommended_mem_request_mib}Mi to prevent crash or latency."
        )
        if spec.replicas == 1:
            tips.append("Add a second replica or configure Horizontal Pod Autoscaler (HPA) for traffic bursts.")

    elif cpu_util > 70.0 or mem_util > 70.0:
        status = "UNDERPROVISIONED_WARNING"
        risk_level = "MODERATE"
        action_required = False
        summary = "Workload running near capacity. Monitor closely during high-traffic periods."
        recommended_cpu_request_m = spec.cpu_request_m
        recommended_cpu_limit_m = spec.cpu_limit_m
        recommended_mem_request_mib = spec.mem_request_mib
        recommended_mem_limit_mib = spec.mem_limit_mib
        tips.append("Capacity is near optimal threshold (70-80%). No immediate reduction advised.")

    else:
        status = "OPTIMAL"
        risk_level = "SAFE"
        action_required = False
        summary = "Workload is in a healthy, cost-effective, and carbon-efficient sweet spot (30-70% utilization)."
        recommended_cpu_request_m = spec.cpu_request_m
        recommended_cpu_limit_m = spec.cpu_limit_m
        recommended_mem_request_mib = spec.mem_request_mib
        recommended_mem_limit_mib = spec.mem_limit_mib
        tips.append("Optimal sizing: resources match current demand safely.")

    # Calculate deltas and percentage reductions
    cpu_delta = spec.cpu_request_m - recommended_cpu_request_m
    cpu_reduction_pct = (cpu_delta / max(1, spec.cpu_request_m)) * 100.0 if spec.cpu_request_m > 0 else 0.0
    mem_delta = spec.mem_request_mib - recommended_mem_request_mib
    mem_reduction_pct = (mem_delta / max(1, spec.mem_request_mib)) * 100.0 if spec.mem_request_mib > 0 else 0.0

    # Generate Kubernetes Patch YAML for administrator inspection (Safe Optimization)
    patch_yaml = f"""# GreenCloud Recommended Safe Optimization Patch
# Review before applying. Execute: kubectl apply -f <this-file>
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {spec.name}
  namespace: {spec.namespace}
spec:
  replicas: {recommended_replicas}
  template:
    spec:
      containers:
      - name: {spec.name}
        resources:
          requests:
            cpu: "{recommended_cpu_request_m}m"
            memory: "{recommended_mem_request_mib}Mi"
          limits:
            cpu: "{recommended_cpu_limit_m}m"
            memory: "{recommended_mem_limit_mib}Mi"
"""

    return RightSizingRecommendation(
        workload_name=spec.name,
        namespace=spec.namespace,
        current_replicas=spec.replicas,
        current_cpu_request_m=spec.cpu_request_m,
        current_cpu_limit_m=spec.cpu_limit_m,
        current_mem_request_mib=spec.mem_request_mib,
        current_mem_limit_mib=spec.mem_limit_mib,
        cpu_utilization_pct=round(cpu_util, 2),
        mem_utilization_pct=round(mem_util, 2),
        recommended_replicas=recommended_replicas,
        recommended_cpu_request_m=recommended_cpu_request_m,
        recommended_cpu_limit_m=recommended_cpu_limit_m,
        recommended_mem_request_mib=recommended_mem_request_mib,
        recommended_mem_limit_mib=recommended_mem_limit_mib,
        cpu_request_delta_m=cpu_delta,
        cpu_request_reduction_pct=round(cpu_reduction_pct, 1),
        mem_request_delta_mib=mem_delta,
        mem_request_reduction_pct=round(mem_reduction_pct, 1),
        status=status,
        risk_level=risk_level,
        action_required=action_required,
        summary=summary,
        tips=tips,
        k8s_patch_yaml=patch_yaml,
    )


def run_full_audit(
    spec: WorkloadSpec,
    metrics: ResourceMetrics,
    grid_region: str = "global",
    pue: float = PUE_PUBLIC_CLOUD
) -> FullOptimizationAudit:
    """
    Performs complete end-to-end evaluation: right-sizing, carbon savings, and cost savings.
    """
    recommendation = analyze_and_recommend(spec, metrics)

    # 1. Carbon baseline vs optimized
    current_carbon = estimate_carbon_footprint(
        cpu_allocated_m=spec.cpu_request_m,
        cpu_used_m=metrics.cpu_used_m,
        mem_allocated_mib=spec.mem_request_mib,
        replicas=spec.replicas,
        grid_region=grid_region,
        pue=pue
    )
    
    optimized_carbon = estimate_carbon_footprint(
        cpu_allocated_m=recommendation.recommended_cpu_request_m,
        cpu_used_m=metrics.cpu_used_m,
        mem_allocated_mib=recommendation.recommended_mem_request_mib,
        replicas=recommendation.recommended_replicas,
        grid_region=grid_region,
        pue=pue
    )

    # 2. Cost baseline vs optimized
    current_cost = estimate_cloud_cost(
        cpu_request_m=spec.cpu_request_m,
        mem_request_mib=spec.mem_request_mib,
        replicas=spec.replicas
    )

    optimized_cost = estimate_cloud_cost(
        cpu_request_m=recommendation.recommended_cpu_request_m,
        mem_request_mib=recommendation.recommended_mem_request_mib,
        replicas=recommendation.recommended_replicas
    )

    # 3. Deltas
    cost_saved = max(0.0, current_cost.monthly_cost_usd - optimized_cost.monthly_cost_usd)
    cost_saved_pct = (cost_saved / max(0.01, current_cost.monthly_cost_usd)) * 100.0

    carbon_saved = max(0.0, current_carbon.monthly_carbon_kg - optimized_carbon.monthly_carbon_kg)
    carbon_saved_pct = (carbon_saved / max(0.01, current_carbon.monthly_carbon_kg)) * 100.0

    return FullOptimizationAudit(
        spec=spec,
        metrics=metrics,
        recommendation=recommendation,
        current_carbon=current_carbon,
        optimized_carbon=optimized_carbon,
        current_cost=current_cost,
        optimized_cost=optimized_cost,
        monthly_cost_saved_usd=cost_saved,
        cost_savings_pct=cost_saved_pct,
        monthly_carbon_saved_kg=carbon_saved,
        carbon_savings_pct=carbon_saved_pct,
    )


# ---------------------------------------------------------------------------
# Backward-compatible legacy advise function
# Matches the original signature so existing app.py code continues to function
# ---------------------------------------------------------------------------
def advise(pod_count: int, cpu_used_m: float, cpu_request_m: int, peak_used_m: float) -> Tuple[float, List[str]]:
    """Legacy interface maintained for backward compatibility."""
    spec = WorkloadSpec(
        name="greencloud",
        replicas=pod_count,
        cpu_request_m=cpu_request_m,
        cpu_limit_m=cpu_request_m * 2,
        mem_request_mib=64,
        mem_limit_mib=128,
    )
    metrics = ResourceMetrics(
        cpu_used_m=cpu_used_m,
        cpu_peak_m=peak_used_m,
        mem_used_mib=32,
        mem_peak_mib=48,
    )
    rec = analyze_and_recommend(spec, metrics)
    return rec.cpu_utilization_pct, rec.tips
