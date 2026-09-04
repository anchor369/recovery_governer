from backend.data_access.payments import (
    get_payment_events_for_order_before_time,
    get_payments_for_order_before_time,
    get_prior_orders_for_customer,
)


def build_payment_method_summary(
    customer_id,
    current_order_id,
    decision_time,
):
    prior_orders = (
        get_prior_orders_for_customer(
            customer_id=customer_id,
            before_time=decision_time,
            exclude_order_id=current_order_id,
        )
    )

    methods = [
        "UPI",
        "CREDIT_CARD",
        "DEBIT_CARD",
        "NETBANKING",
    ]

    first_method_counts = {
        method: 0
        for method in methods
    }

    method_history = {
        method: {
            "attempt_count": 0,
            "resolved_count": 0,
            "success_count": 0,
            "success_rate": 0.0,
        }
        for method in methods
    }

    for order in prior_orders:
        order_id = order["order_id"]

        payments = (
            get_payments_for_order_before_time(
                order_id=order_id,
                before_time=decision_time,
            )
        )

        if not payments:
            continue

        first_method = (
            payments[0]["method"].upper()
        )

        if first_method in first_method_counts:
            first_method_counts[
                first_method
            ] += 1

        events = (
            get_payment_events_for_order_before_time(
                order_id=order_id,
                before_time=decision_time,
            )
        )

        latest_status_by_payment = {}

        for event in events:
            latest_status_by_payment[
                event["payment_id"]
            ] = event[
                "event_type"
            ].upper()

        for payment in payments:
            method = payment[
                "method"
            ].upper()

            if method not in method_history:
                continue

            stats = method_history[
                method
            ]

            stats[
                "attempt_count"
            ] += 1

            status = (
                latest_status_by_payment.get(
                    payment["payment_id"]
                )
            )

            if status in {
                "CAPTURED",
                "FAILED",
            }:
                stats[
                    "resolved_count"
                ] += 1

            if status == "CAPTURED":
                stats[
                    "success_count"
                ] += 1

    for stats in method_history.values():
        if stats["resolved_count"] > 0:
            stats["success_rate"] = (
                stats["success_count"]
                / stats["resolved_count"]
            )

    return {
        "prior_upi_count":
            first_method_counts["UPI"],

        "prior_credit_card_count":
            first_method_counts[
                "CREDIT_CARD"
            ],

        "prior_debit_card_count":
            first_method_counts[
                "DEBIT_CARD"
            ],

        "prior_netbanking_count":
            first_method_counts[
                "NETBANKING"
            ],

        "prior_upi_attempt_count":
            method_history[
                "UPI"
            ]["attempt_count"],

        "prior_upi_success_count":
            method_history[
                "UPI"
            ]["success_count"],

        "prior_upi_success_rate":
            method_history[
                "UPI"
            ]["success_rate"],

        "prior_credit_card_attempt_count":
            method_history[
                "CREDIT_CARD"
            ]["attempt_count"],

        "prior_credit_card_success_count":
            method_history[
                "CREDIT_CARD"
            ]["success_count"],

        "prior_credit_card_success_rate":
            method_history[
                "CREDIT_CARD"
            ]["success_rate"],

        "prior_debit_card_attempt_count":
            method_history[
                "DEBIT_CARD"
            ]["attempt_count"],

        "prior_debit_card_success_count":
            method_history[
                "DEBIT_CARD"
            ]["success_count"],

        "prior_debit_card_success_rate":
            method_history[
                "DEBIT_CARD"
            ]["success_rate"],

        "prior_netbanking_attempt_count":
            method_history[
                "NETBANKING"
            ]["attempt_count"],

        "prior_netbanking_success_count":
            method_history[
                "NETBANKING"
            ]["success_count"],

        "prior_netbanking_success_rate":
            method_history[
                "NETBANKING"
            ]["success_rate"],
    }
