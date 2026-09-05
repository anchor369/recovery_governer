from typing import Any

from pydantic import BaseModel


class MetricsResponse(BaseModel):
    total_recovery_cases: int
    open_cases: int
    closed_cases: int
    recovered_cases: int
    recovered_order_value_minor: int
    action_counts: dict[str, int]
    canonical_benchmarks: list[dict[str, Any]]
    canonical_thresholds: list[dict[str, Any]]
