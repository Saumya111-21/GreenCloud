"""
Comprehensive demonstration and verification script for Phase 1.
Runs full audits across different workload profiles and outputs verified results.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.models import WorkloadSpec, ResourceMetrics
from engine.advisor import run_full_audit

def main():
    print("=" * 80)
    print("  GREENCLOUD: PHASE 1 CALCULATION & OPTIMIZATION ENGINE VERIFICATION")
    print("=" * 80)

    workloads = [
        (
            WorkloadSpec(
                name="greencloud-k8s-pod",
                namespace="default",
                replicas=2,
                cpu_request_m=100,
                cpu_limit_m=250,
                mem_request_mib=64,
                mem_limit_mib=128,
                description="Your actual project baseline (before optimization)"
            ),
            ResourceMetrics(
                cpu_used_m=0.25,
                cpu_peak_m=2.0,
                mem_used_mib=35.0,
                mem_peak_mib=45.0,
                is_simulated=False
            )
        ),
        (
            WorkloadSpec(
                name="auth-service",
                namespace="production",
                replicas=3,
                cpu_request_m=500,
                cpu_limit_m=1000,
                mem_request_mib=1024,
                mem_limit_mib=2048,
                description="Microservice with idle memory allocation"
            ),
            ResourceMetrics(
                cpu_used_m=45.0,
                cpu_peak_m=120.0,
                mem_used_mib=180.0,
                mem_peak_mib=240.0,
                is_simulated=True
            )
        ),
        (
            WorkloadSpec(
                name="heavy-data-processor",
                namespace="analytics",
                replicas=1,
                cpu_request_m=200,
                cpu_limit_m=400,
                mem_request_mib=512,
                mem_limit_mib=1024,
                description="Under-provisioned batch job under high load"
            ),
            ResourceMetrics(
                cpu_used_m=185.0,
                cpu_peak_m=380.0,
                mem_used_mib=480.0,
                mem_peak_mib=950.0,
                is_simulated=True
            )
        )
    ]

    for spec, metrics in workloads:
        print(f"\n>> Workload: {spec.name} ({spec.description})")
        print(f"   Simulated: {spec.is_simulated} | Metrics Simulated: {metrics.is_simulated}")
        print(f"   Current Spec : {spec.replicas} replicas | CPU Request: {spec.cpu_request_m}m | RAM Request: {spec.mem_request_mib}Mi")
        print(f"   Measured Peak: CPU: {metrics.cpu_peak_m}m | RAM: {metrics.mem_peak_mib}Mi")
        
        audit = run_full_audit(spec, metrics, grid_region="india")
        rec = audit.recommendation
        
        cpu_delta_str = f"-{rec.cpu_request_delta_m}m" if rec.cpu_request_delta_m >= 0 else f"+{abs(rec.cpu_request_delta_m)}m"
        print(f"   Status       : [{rec.status}] - Risk: {rec.risk_level}")
        print(f"   Recommended  : {rec.recommended_replicas} replicas | CPU: {rec.recommended_cpu_request_m}m (delta: {cpu_delta_str}) | RAM: {rec.recommended_mem_request_mib}Mi")
        print(f"   Cost (Mo)    : ${audit.current_cost.monthly_cost_usd:.2f} -> ${audit.optimized_cost.monthly_cost_usd:.2f} | SAVINGS: ${audit.monthly_cost_saved_usd:.2f} ({audit.cost_savings_pct:.1f}%)")
        print(f"   Carbon (Mo)  : {audit.current_carbon.monthly_carbon_kg:.2f} kg -> {audit.optimized_carbon.monthly_carbon_kg:.2f} kg | REDUCTION: {audit.monthly_carbon_saved_kg:.2f} kg ({audit.carbon_savings_pct:.1f}%)")
        print(f"   Offset Equiv : Saving is equivalent to planting {audit.current_carbon.trees_offset_equivalent - audit.optimized_carbon.trees_offset_equivalent:.1f} trees/yr")
        print("   Key Tips     :")
        for tip in rec.tips:
            print(f"     * {tip}")
        print("   Generated Safe K8s Patch Preview:")
        for line in rec.k8s_patch_yaml.strip().split("\n")[:8]:
            print(f"     | {line}")

if __name__ == "__main__":
    main()
