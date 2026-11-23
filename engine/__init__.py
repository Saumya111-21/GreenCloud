"""
GreenCloud Calculation and Optimization Engine Package.
"""

from .models import (
    WorkloadSpec,
    ResourceMetrics,
    RightSizingRecommendation,
    CarbonEstimate,
    CostEstimate,
    FullOptimizationAudit,
)
from .carbon import (
    estimate_carbon_footprint,
    calculate_power_watts,
    REGIONAL_GRID_INTENSITY,
    PUE_PUBLIC_CLOUD,
    PUE_PRIVATE_CLOUD,
)
from .cost import estimate_cloud_cost
from .advisor import analyze_and_recommend, run_full_audit, advise
from .collector import (
    MetricsCollector,
    CollectorSnapshot,
    get_collector,
    detect_runtime_environment,
    SOURCE_CGROUP_V2,
    SOURCE_CGROUP_V1,
    SOURCE_HOST,
)
from .prometheus import (
    format_prometheus_metrics,
    parse_and_validate_prometheus_text,
    PROMETHEUS_CONTENT_TYPE,
)

__all__ = [
    "WorkloadSpec",
    "ResourceMetrics",
    "RightSizingRecommendation",
    "CarbonEstimate",
    "CostEstimate",
    "FullOptimizationAudit",
    "estimate_carbon_footprint",
    "calculate_power_watts",
    "REGIONAL_GRID_INTENSITY",
    "PUE_PUBLIC_CLOUD",
    "PUE_PRIVATE_CLOUD",
    "estimate_cloud_cost",
    "analyze_and_recommend",
    "run_full_audit",
    "advise",
    "MetricsCollector",
    "CollectorSnapshot",
    "get_collector",
    "detect_runtime_environment",
    "SOURCE_CGROUP_V2",
    "SOURCE_CGROUP_V1",
    "SOURCE_HOST",
    "format_prometheus_metrics",
    "parse_and_validate_prometheus_text",
    "PROMETHEUS_CONTENT_TYPE",
]
