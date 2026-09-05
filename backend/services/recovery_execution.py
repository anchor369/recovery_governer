import logging
import uuid
from datetime import (
    datetime,
    timezone,
)

from backend.data_access.recovery import (
    create_recovery_action,
    transition_pending_recovery_action,
)

from backend.services.payment_truth import (
    evaluate_order_truth,
)

from simulator.models import (
    ActionType,
)

from simulator.action_codec import (
    action_to_label,
)


logger = logging.getLogger(__name__)


def create_pending_recovery_action(
    decision_id,
    chosen_action,
):
    """
    Create the operational action corresponding
    to the Governor's final decision.
    """

    action_id = (
        "A_"
        + uuid.uuid4().hex[:12]
    )

    label = action_to_label(
        chosen_action
    )

    policy_checks = {
        "governor_approved": True,
        "action_label": label,
    }

    # NO_ACTION is still stored so that the
    # full decision lifecycle is auditable.
    # But there is nothing external to execute.
    if (
        chosen_action.action_type
        == ActionType.NO_ACTION
    ):
        return create_recovery_action(
            action_id=action_id,
            decision_id=decision_id,
            action_type=label,
            execution_status=(
                "NOT_REQUIRED"
            ),
            blocked_reason=None,
            policy_checks=policy_checks,
            executed_at=(
                datetime.now(
                    timezone.utc
                )
            ),
        )

    return create_recovery_action(
        action_id=action_id,
        decision_id=decision_id,
        action_type=label,
        execution_status="PENDING",
        blocked_reason=None,
        policy_checks=policy_checks,
        executed_at=None,
    )


def execute_recovery_action(
    order_id,
    action,
):
    """
    Simulated executor.

    Before executing, payment truth is checked
    again to prevent intervention after the
    customer has already paid.
    """

    status = (
        action["execution_status"]
    )

    # NO_ACTION reaches here as NOT_REQUIRED.
    if status == "NOT_REQUIRED":
        logger.debug(
            "Recovery action requires no execution: action_id=%s",
            action["action_id"],
        )
        return action

    if status in {"EXECUTED", "BLOCKED"}:
        logger.debug(
            "Recovery action already processed: action_id=%s status=%s",
            action["action_id"],
            status,
        )
        return {
            **action,
            "execution_result": "ALREADY_PROCESSED",
            "transition_applied": False,
        }

    if status != "PENDING":
        raise ValueError(
            "Only PENDING recovery actions "
            "can be executed."
        )

    truth = evaluate_order_truth(
        order_id
    )

    # Race-condition protection:
    # payment recovered after decision but
    # before execution.
    if truth == "PAID":
        execution_status = "BLOCKED"
        blocked_reason = (
            "ORDER_ALREADY_PAID_"
            "BEFORE_EXECUTION"
        )
        executed_at = None

    # Never intervene when payment truth
    # itself is unresolved.
    elif truth == "UNCERTAIN":
        execution_status = "BLOCKED"
        blocked_reason = (
            "PAYMENT_STATE_UNCERTAIN_"
            "BEFORE_EXECUTION"
        )
        executed_at = None

    # In the buildathon demo this represents
    # successful hand-off to the appropriate
    # nudge / switch / offer execution channel.
    else:
        execution_status = "EXECUTED"
        blocked_reason = None
        executed_at = datetime.now(
            timezone.utc
        )

    transition = transition_pending_recovery_action(
        action_id=action["action_id"],
        execution_status=execution_status,
        blocked_reason=blocked_reason,
        executed_at=executed_at,
    )

    if transition["transition_applied"]:
        execution_result = (
            "EXECUTED_NOW"
            if execution_status == "EXECUTED"
            else "BLOCKED_BY_PAYMENT_TRUTH"
        )
        if execution_status == "EXECUTED":
            logger.info(
                "Recovery action executed: action_id=%s order_id=%s",
                action["action_id"],
                order_id,
            )
        else:
            logger.info(
                "Recovery action blocked by payment truth: action_id=%s order_id=%s reason=%s",
                action["action_id"],
                order_id,
                blocked_reason,
            )
    else:
        execution_result = "ALREADY_PROCESSED"
        logger.debug(
            "Recovery action transition lost race: action_id=%s requested_status=%s",
            action["action_id"],
            execution_status,
        )

    return {
        **transition["action"],
        "execution_result": execution_result,
        "transition_applied": transition["transition_applied"],
    }
