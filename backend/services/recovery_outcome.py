import logging
import uuid
from datetime import (
    datetime,
    timezone,
)

from backend.data_access.recovery import (
    create_recovered_outcome_and_close_case,
    get_recovery_outcome_context,
)


logger = logging.getLogger(__name__)


def record_recovered_payment(
    recovery_case_id,
    action_id,
    payment_id,
    outcome_time=None,
):
    """
    Record a successful recovery only when
    payment truth proves that the supplied
    payment was captured for the same Order.
    """

    if outcome_time is None:
        outcome_time = datetime.now(
            timezone.utc
        )

    context = (
        get_recovery_outcome_context(
            recovery_case_id=(
                recovery_case_id
            ),
            action_id=action_id,
            payment_id=payment_id,
        )
    )

    if context is None:
        raise ValueError(
            "Recovery case, action, or payment "
            "relationship could not be resolved."
        )

    if context["closed_at"] is not None:
        raise ValueError(
            "Recovery case is already closed."
        )

    # Critical relationship check:
    # the successful payment must belong to
    # the exact Order being recovered.
    if (
        context["payment_order_id"]
        != context["recovery_order_id"]
    ):
        raise ValueError(
            "Payment belongs to a different order."
        )

    # We only attribute an outcome to an action
    # that actually reached execution.
    if (
        context["execution_status"]
        not in {
            "EXECUTED",
            "NOT_REQUIRED",
        }
    ):
        raise ValueError(
            "Recovery action was not executed."
        )

    # Most important financial-truth check.
    #
    # Do not infer recovery from the ML model,
    # action execution, or materialized status.
    # The latest payment event itself must say
    # CAPTURED.
    if (
        context[
            "latest_payment_event_type"
        ]
        != "CAPTURED"
    ):
        raise ValueError(
            "Payment is not confirmed CAPTURED."
        )

    opened_at = context[
        "opened_at"
    ]

    time_to_recovery_seconds = max(
        int(
            (
                outcome_time
                - opened_at
            ).total_seconds()
        ),
        0,
    )

    outcome_id = (
        "OUT_"
        + uuid.uuid4().hex[:12]
    )

    result = (
        create_recovered_outcome_and_close_case(
            outcome_id=outcome_id,
            recovery_case_id=(
                recovery_case_id
            ),
            action_id=action_id,
            payment_id=payment_id,

            # payments currently does not have
            # its own amount column, therefore
            # this prototype records recovered
            # Order value.
            recovered_amount_minor=(
                context[
                    "order_amount_minor"
                ]
            ),

            outcome_time=(
                outcome_time
            ),

            time_to_recovery_seconds=(
                time_to_recovery_seconds
            ),
        )
    )

    logger.info(
        "Verified recovery persisted and case closed: recovery_case_id=%s action_id=%s payment_id=%s",
        recovery_case_id,
        action_id,
        payment_id,
    )

    return result
