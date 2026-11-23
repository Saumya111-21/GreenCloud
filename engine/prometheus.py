"""
Prometheus Metric Exposition and Verification Module for GreenCloud.
Generates genuine Prometheus/OpenMetrics text exposition format metrics.
"""

from typing import Dict, Any, List
from .collector import CollectorSnapshot
from .models import FullOptimizationAudit

PROMETHEUS_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"


def format_prometheus_metrics(
    snapshot: CollectorSnapshot,
    audit: FullOptimizationAudit,
    app_version: str = "2.0.0"
) -> str:
    """
    Renders telemetry, carbon, and FinOps metrics in standard Prometheus text format.
    Strictly adheres to Prometheus Exposition Format specifications.
    """
    lines: List[str] = []

    def add_gauge(name: str, help_text: str, value: float, labels: Dict[str, Any] = None):
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} gauge")
        if labels:
            label_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
            lines.append(f"{name}{{{label_str}}} {value}")
        else:
            lines.append(f"{name} {value}")

    # 1. Health and service info
    add_gauge(
        "greencloud_up",
        "1 if the GreenCloud telemetry and monitoring service is healthy",
        1.0,
        {"version": app_version, "environment": snapshot.metric_source}
    )

    # 2. CPU Metrics
    add_gauge(
        "greencloud_cpu_usage_percent",
        "Current normalized CPU utilization percentage (0 - 100)",
        round(snapshot.cpu_percent, 2)
    )
    add_gauge(
        "greencloud_cpu_used_millicores",
        "Instantaneous CPU usage consumed in millicores (1000m = 1 core)",
        round(snapshot.cpu_used_m, 2)
    )
    add_gauge(
        "greencloud_cpu_peak_millicores",
        "Measured historical peak CPU usage in millicores",
        round(snapshot.cpu_peak_m, 2)
    )
    add_gauge(
        "greencloud_cpu_request_millicores",
        "Configured Kubernetes CPU request reservation in millicores",
        float(audit.spec.cpu_request_m)
    )
    add_gauge(
        "greencloud_cpu_limit_millicores",
        "Configured Kubernetes CPU limit ceiling in millicores",
        float(audit.spec.cpu_limit_m)
    )

    # 3. Memory Metrics
    mem_bytes = int(snapshot.mem_used_mib * 1024 * 1024)
    add_gauge(
        "greencloud_memory_used_bytes",
        "Memory currently consumed in bytes",
        float(mem_bytes)
    )
    add_gauge(
        "greencloud_memory_used_mib",
        "Memory currently consumed in MiB",
        round(snapshot.mem_used_mib, 2)
    )
    add_gauge(
        "greencloud_memory_peak_mib",
        "Measured historical peak memory in MiB",
        round(snapshot.mem_peak_mib, 2)
    )
    add_gauge(
        "greencloud_memory_usage_percent",
        "Current memory utilization percentage",
        round(snapshot.mem_percent, 2)
    )

    # 4. Energy and Sustainability (GreenCloud Core)
    add_gauge(
        "greencloud_power_consumption_watts",
        "Instantaneous estimated workload power draw in Watts",
        round(audit.current_carbon.power_watts, 2),
        {"pue": str(audit.current_carbon.pue), "is_estimate": "true"}
    )
    add_gauge(
        "greencloud_monthly_energy_kwh",
        "Projected monthly electrical energy consumption in kWh",
        round(audit.current_carbon.monthly_energy_kwh, 2),
        {"is_estimate": "true"}
    )
    add_gauge(
        "greencloud_monthly_carbon_emissions_kg",
        "Projected monthly CO2e greenhouse gas emissions in kilograms",
        round(audit.current_carbon.monthly_carbon_kg, 2),
        {"grid_region": audit.current_carbon.grid_region, "intensity_g_per_kwh": str(audit.current_carbon.carbon_intensity_g_per_kwh), "is_estimate": "true"}
    )
    add_gauge(
        "greencloud_monthly_carbon_savings_kg",
        "Estimated monthly CO2e carbon reduction achievable through right-sizing in kg",
        round(audit.monthly_carbon_saved_kg, 2),
        {"is_estimate": "true"}
    )

    # 5. Cloud FinOps & Cost
    add_gauge(
        "greencloud_monthly_cost_usd",
        "Estimated monthly cloud infrastructure cost in USD",
        round(audit.current_cost.monthly_cost_usd, 2),
        {"is_estimate": "true"}
    )
    add_gauge(
        "greencloud_monthly_cost_savings_usd",
        "Estimated monthly cost savings from right-sizing in USD",
        round(audit.monthly_cost_saved_usd, 2),
        {"is_estimate": "true"}
    )

    # 6. Cluster & Topology
    add_gauge(
        "greencloud_replicas_count",
        "Active pod replicas count",
        float(audit.spec.replicas)
    )
    add_gauge(
        "greencloud_recommended_replicas_count",
        "Intelligent advisor recommended replica count",
        float(audit.recommendation.recommended_replicas)
    )

    return "\n".join(lines) + "\n"


def parse_and_validate_prometheus_text(content: str) -> Dict[str, Any]:
    """
    Validates that a string complies with the Prometheus text exposition specification.
    Returns parsed metrics and validation status.
    """
    lines = content.strip().split("\n")
    metrics: Dict[str, float] = {}
    help_defs: Dict[str, str] = {}
    type_defs: Dict[str, str] = {}

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("# HELP"):
            parts = line.split(maxsplit=3)
            if len(parts) >= 3:
                help_defs[parts[2]] = parts[3] if len(parts) > 3 else ""
        elif line.startswith("# TYPE"):
            parts = line.split(maxsplit=3)
            if len(parts) >= 4:
                type_defs[parts[2]] = parts[3]
        else:
            # Sample line: metric_name{labels} value
            parts = line.split()
            if len(parts) == 2:
                metric_name_raw = parts[0]
                val = float(parts[1])
                name_clean = metric_name_raw.split("{")[0]
                metrics[name_clean] = val

    valid = (
        len(metrics) > 0 and
        len(help_defs) > 0 and
        len(type_defs) > 0 and
        "greencloud_up" in metrics and
        "greencloud_cpu_used_millicores" in metrics
    )

    return {
        "valid": valid,
        "metric_count": len(metrics),
        "metrics": metrics,
        "types": type_defs,
        "helps": help_defs
    }
