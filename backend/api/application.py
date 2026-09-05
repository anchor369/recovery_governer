from datetime import datetime, timezone

from backend.api.serialization import (
    runtime_signals_from_request,
    serialize_workflow_result,
)
from backend.data_access.payments import get_order
from backend.services.recovery_engine import run_recovery_workflow
from backend.services.recovery_outcome import record_recovered_payment


class OrderNotFoundError(LookupError):
    pass


class RecoveryOutcomeLinkNotFoundError(LookupError):
    pass


class RecoveryOutcomeConflictError(RuntimeError):
    pass


def serialize_recovery_outcome(result):
    outcome = result['outcome']
    recovery_case = result['case']
    return {
        'recovery_case_id': recovery_case['recovery_case_id'],
        'order_id': recovery_case['order_id'],
        'outcome_id': outcome['outcome_id'],
        'outcome_type': outcome['outcome_type'],
        'recovered_payment_id': outcome['payment_id'],
        'recovered_amount_minor': outcome['recovered_amount_minor'],
        'case_status': recovery_case['status'],
        'closure_reason': recovery_case['closure_reason'],
    }


def record_outcome_or_raise(recovery_case_id, request):
    try:
        return record_recovered_payment(
            recovery_case_id=recovery_case_id,
            action_id=request.action_id,
            payment_id=request.payment_id,
        )
    except ValueError as error:
        if 'relationship could not be resolved' in str(error):
            raise RecoveryOutcomeLinkNotFoundError(recovery_case_id) from error
        raise RecoveryOutcomeConflictError(recovery_case_id) from error


def run_order_recovery(order_id, request, decision_service):
    if get_order(order_id) is None:
        raise OrderNotFoundError(order_id)

    result = run_recovery_workflow(
        order_id=order_id,
        decision_time=datetime.now(timezone.utc),
        runtime_signals=runtime_signals_from_request(request),
        decision_service=decision_service,
    )
    return serialize_workflow_result(result)


def attribute_recovery_outcome(recovery_case_id, request):
    result = record_outcome_or_raise(recovery_case_id, request)
    return serialize_recovery_outcome(result)
