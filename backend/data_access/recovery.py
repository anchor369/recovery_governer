"""Compatibility facade for recovery persistence operations."""

from backend.data_access.recovery_actions import (
    _transition_pending_recovery_action,
    create_recovery_action,
    transition_pending_recovery_action,
)
from backend.data_access.recovery_cases import (
    WORKFLOW_FAILURE_REASONS,
    close_recovery_case_for_workflow_failure,
    create_recovery_case,
    get_active_recovery_case_for_order,
)
from backend.data_access.recovery_decisions import (
    _insert_decision_action_score,
    _insert_recovery_decision,
    create_decision_action_score,
    create_recovery_decision,
    create_recovery_decision_audit_bundle,
    get_recovery_decision,
)
from backend.data_access.recovery_outcomes import (
    create_recovered_outcome_and_close_case,
    get_recovery_outcome_context,
)


__all__ = (
    "WORKFLOW_FAILURE_REASONS",
    "close_recovery_case_for_workflow_failure",
    "create_decision_action_score",
    "create_recovered_outcome_and_close_case",
    "create_recovery_action",
    "create_recovery_case",
    "create_recovery_decision",
    "create_recovery_decision_audit_bundle",
    "get_active_recovery_case_for_order",
    "get_recovery_decision",
    "get_recovery_outcome_context",
    "transition_pending_recovery_action",
)
