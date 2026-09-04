from backend.data_access.payments import (
    get_order,
    get_payments_for_order,
    get_payment_events_for_order_before_time,
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

def evaluate_order_truth_at_time(
    order_id,
    before_time,
):
    order = get_order(order_id)

    if order is None:
        return "ORDER_NOT_FOUND"

    events = (
        get_payment_events_for_order_before_time(
            order_id=order_id,
            before_time=before_time,
        )
    )

    if not events:
        return "UNCERTAIN"

    latest_status_by_payment = {}

    for event in events:
        latest_status_by_payment[
            event["payment_id"]
        ] = event["event_type"].upper()

    latest_statuses = list(
        latest_status_by_payment.values()
    )

    if "CAPTURED" in latest_statuses:
        return "PAID"

    if any(
        status in {
            "CREATED",
            "AUTHORIZED",
        }
        for status in latest_statuses
    ):
        return "UNCERTAIN"

    if latest_statuses and all(
        status == "FAILED"
        for status in latest_statuses
    ):
        return "UNPAID"

    return "UNCERTAIN"