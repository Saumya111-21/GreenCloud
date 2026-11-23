"""
GreenCloud Advisor Facade.
Provides seamless backward-compatibility for existing imports and tests.
Delegates core calculations to engine.advisor.
"""

from engine.advisor import advise, analyze_and_recommend, run_full_audit
from engine.models import WorkloadSpec, ResourceMetrics

if __name__ == "__main__":
    print("=== GreenCloud Intelligent Optimization Engine (Legacy CLI Test) ===")
    util, tips = advise(pod_count=2, cpu_used_m=0.25, cpu_request_m=100, peak_used_m=2)
    print(f"Utilization: {util:.2f}%")
    for tip in tips:
        print("-", tip)

    print("\n=== Full Audit Demo ===")
    spec = WorkloadSpec(name="greencloud-demo", replicas=2, cpu_request_m=100, cpu_limit_m=250, mem_request_mib=128, mem_limit_mib=256)
    metrics = ResourceMetrics(cpu_used_m=0.25, cpu_peak_m=2.0, mem_used_mib=32.0, mem_peak_mib=45.0)
    audit = run_full_audit(spec, metrics, grid_region="india")
    print(f"Status: {audit.recommendation.status}")
    print(f"Monthly Cost Saved: ${audit.monthly_cost_saved_usd:.2f} ({audit.cost_savings_pct:.1f}%)")
    print(f"Monthly Carbon Saved: {audit.monthly_carbon_saved_kg:.2f} kg CO2e ({audit.carbon_savings_pct:.1f}%)")
