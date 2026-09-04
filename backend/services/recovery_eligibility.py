from backend.data_access.payments import get_payments_for_order
from backend.data_access.recovery import get_active_recovery_case_for_order
from backend.services.payment_truth import evaluate_order_truth

def evaluate_recovery_eligibility(order_id):
    truth = evaluate_order_truth(order_id)

    if truth == "ORDER_NOT_FOUND":
        return {
            "eligible": False,
            "reason": "ORDER_NOT_FOUND"
        }

    if truth == "PAID":
        return {
            "eligible": False,
            "reason": "ORDER_ALREADY_PAID"
        }

    if truth == "UNCERTAIN":
        return {
            "eligible": False,
            "reason": "PAYMENT_STATE_UNCERTAIN"
        }

    existing_case = get_active_recovery_case_for_order(order_id)

    if existing_case is not None:
        return {
            "eligible": False,
            "reason": "RECOVERY_CASE_ALREADY_EXISTS"
        }

    payments = get_payments_for_order(order_id)

    failed_payments = [
        payment
        for payment in payments
        if payment["status"] == "FAILED"
    ]

    failure_count = len(failed_payments)

    if failure_count == 0:
        return {
            "eligible": False,
            "reason": "NO_CONFIRMED_FAILURE"
        }

    if failure_count == 1:
        return {
            "eligible": False,
            "reason": "ALLOW_NATURAL_RETRY"
        }

    return {
        "eligible": True,
        "reason": "MULTIPLE_CONFIRMED_FAILURES"
    }