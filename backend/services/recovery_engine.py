import uuid

from backend.data_access.recovery import create_recovery_case
from backend.services.recovery_eligibility import (
    evaluate_recovery_eligibility
)


def open_recovery_case_if_eligible(order_id):
    eligibility = evaluate_recovery_eligibility(order_id)

    if not eligibility["eligible"]:
        return {
            "opened": False,
            "reason": eligibility["reason"],
            "case": None
        }

    recovery_case_id = f"RC_{uuid.uuid4().hex[:12]}"

    recovery_case = create_recovery_case(
        recovery_case_id=recovery_case_id,
        order_id=order_id
    )

    return {
        "opened": True,
        "reason": "RECOVERY_CASE_OPENED",
        "case": recovery_case
    }