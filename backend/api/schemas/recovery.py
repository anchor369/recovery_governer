from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RuntimeSignalsRequest(BaseModel):
    available_upi: bool = True
    available_credit_card: bool = True
    available_debit_card: bool = True
    available_netbanking: bool = True
    observed_rail_health: float = Field(default=0.9, ge=0.0, le=1.0)
    customer_active: bool = False


class RecoveryRunResponse(BaseModel):
    workflow_state: str
    reason: str
    case: dict[str, Any] | None = None
    decision: dict[str, Any] | None = None
    chosen_action: str | None = None
    execution_action: dict[str, Any] | None = None
    candidate_action_scores: list[dict[str, Any]] = Field(default_factory=list)


class RecoveryOutcomeRequest(BaseModel):
    action_id: str = Field(min_length=1)
    payment_id: str = Field(min_length=1)


class RecoveryOutcomeResponse(BaseModel):
    recovery_case_id: str
    order_id: str
    outcome_id: str
    outcome_type: str
    recovered_payment_id: str
    recovered_amount_minor: int
    case_status: str
    closure_reason: str


class RecoveryViewResponse(BaseModel):
    order_id: str
    financial_truth: str
    recovery_case: dict[str, Any] | None = None
    decision: dict[str, Any] | None = None
    candidate_action_scores: list[dict[str, Any]] = Field(default_factory=list)
    action: dict[str, Any] | None = None
    outcome: dict[str, Any] | None = None


class TimelineItem(BaseModel):
    timestamp: datetime
    type: str
    title: str
    details: dict[str, Any]


class RecoveryCaseSummary(BaseModel):
    order_id: str
    recovery_case_id: str
    status: str
    closure_reason: str | None = None
    chosen_action: str | None = None
    execution_status: str | None = None
    outcome_type: str | None = None
    opened_at: datetime
    closed_at: datetime | None = None
