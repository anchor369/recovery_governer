import logging
import uuid
from dataclasses import (
    dataclass,
)

from backend.data_access.recovery import (
    close_recovery_case_for_workflow_failure,
    create_recovery_case,
)

from backend.services.recovery_audit import (
    persist_operational_decision,
)

from backend.services.recovery_eligibility import (
    evaluate_recovery_eligibility,
)

from backend.services.recovery_execution import (
    create_pending_recovery_action,
    execute_recovery_action,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecoveryWorkflowResult:
    workflow_state: str
    reason: str
    case: dict | None
    decision: object | None
    audit: dict | None = None
    action: dict | None = None


def open_recovery_case_if_eligible(
    order_id,
):
    eligibility = (
        evaluate_recovery_eligibility(
            order_id
        )
    )

    if not eligibility["eligible"]:
        return {
            "opened": False,
            "reason": eligibility["reason"],
            "case": None,
        }

    recovery_case_id = (
        "RC_"
        + uuid.uuid4().hex[:12]
    )

    recovery_case = (
        create_recovery_case(
            recovery_case_id=(
                recovery_case_id
            ),
            order_id=order_id,
        )
    )

    return {
        "opened": True,
        "reason": (
            "RECOVERY_CASE_OPENED"
        ),
        "case": recovery_case,
    }


def run_recovery_workflow(
    order_id,
    decision_time,
    runtime_signals,
    decision_service,
):
    case_result = (
        open_recovery_case_if_eligible(
            order_id
        )
    )

    if not case_result["opened"]:
        reason = case_result[
            "reason"
        ]

        if reason == "ORDER_ALREADY_PAID":
            workflow_state = "STOP"

        elif (
            reason
            == "PAYMENT_STATE_UNCERTAIN"
        ):
            workflow_state = (
                "WAIT_FOR_TRUTH"
            )

        elif (
            reason
            == "ALLOW_NATURAL_RETRY"
        ):
            workflow_state = (
                "ALLOW_NATURAL_RETRY"
            )

        elif (
            reason
            == "RECOVERY_CASE_ALREADY_EXISTS"
        ):
            workflow_state = (
                "RECOVERY_ALREADY_OPEN"
            )

        else:
            workflow_state = (
                "NO_RECOVERY"
            )

        return RecoveryWorkflowResult(
            workflow_state=(
                workflow_state
            ),
            reason=reason,
            case=None,
            decision=None,
            audit=None,
            action=None,
        )

    recovery_case = (
        case_result["case"]
    )

    logger.info(
        "Recovery case opened: recovery_case_id=%s order_id=%s",
        recovery_case["recovery_case_id"],
        order_id,
    )

    failure_reason = "DECISION_FAILED"

    try:
        decision = (
            decision_service
            .decide_for_order(
                current_order_id=(
                    order_id
                ),
                decision_time=(
                    decision_time
                ),
                runtime_signals=(
                    runtime_signals
                ),
            )
        )

        failure_reason = "AUDIT_FAILED"

        audit = (
            persist_operational_decision(
                recovery_case_id=(
                    recovery_case[
                        "recovery_case_id"
                    ]
                ),
                prediction_time=(
                    decision_time
                ),
                operational_decision=(
                    decision
                ),
                governor=(
                    decision_service
                    .governor
                ),
            )
        )

        decision_id = (
            audit[
                "decision"
            ][
                "decision_id"
            ]
        )

        chosen_action = (
            decision
            .governor_decision
            .chosen_action
        )

        failure_reason = "ACTION_CREATION_FAILED"

        pending_action = (
            create_pending_recovery_action(
                decision_id=decision_id,
                chosen_action=(
                    chosen_action
                ),
            )
        )

        logger.info(
            "Recovery decision completed: recovery_case_id=%s decision_id=%s action_id=%s",
            recovery_case["recovery_case_id"],
            decision_id,
            pending_action["action_id"],
        )

    except Exception as original_error:
        try:
            close_recovery_case_for_workflow_failure(
                recovery_case_id=(
                    recovery_case[
                        "recovery_case_id"
                    ]
                ),
                closure_reason=failure_reason,
            )
        except Exception as persistence_error:
            logger.exception(
                "Recovery workflow failure could not be persisted: recovery_case_id=%s stage=%s",
                recovery_case["recovery_case_id"],
                failure_reason,
            )
            original_error.add_note(
                "Recovery workflow failure-state persistence "
                f"also failed: {persistence_error}"
            )
            raise original_error from persistence_error

        logger.exception(
            "Recovery workflow failed and case was closed: recovery_case_id=%s stage=%s",
            recovery_case["recovery_case_id"],
            failure_reason,
        )
        raise

    executed_action = (
        execute_recovery_action(
            order_id=order_id,
            action=pending_action,
        )
    )

    return RecoveryWorkflowResult(
        workflow_state="DECIDED",
        reason=(
            "RECOVERY_DECISION_CREATED"
        ),
        case=recovery_case,
        decision=decision,
        audit=audit,
        action=executed_action,
    )
