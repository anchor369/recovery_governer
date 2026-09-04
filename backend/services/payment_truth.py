from backend.data_access.payments import (
    get_order,
    get_payments_for_order,
)


def evaluate_order_truth(order_id):
    order = get_order(order_id)

    if order is None:
        return "ORDER_NOT_FOUND"

    payments = get_payments_for_order(order_id)

    payment_statuses = [
        payment["status"]
        for payment in payments
    ]

    if "CAPTURED" in payment_statuses:
        return "PAID"

    if any(
        status in {"CREATED", "AUTHORIZED"}
        for status in payment_statuses
    ):
        return "UNCERTAIN"

    return "UNPAID"