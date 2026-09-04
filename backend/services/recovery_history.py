from statistics import median

from backend.data_access.payments import (
    get_customer,
    get_order,
    get_prior_orders_for_customer,
)
from backend.services.payment_truth import (
    evaluate_order_truth_at_time,
)


def build_prior_order_summary(
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

    prior_checkout_count = len(
        prior_orders
    )

    prior_success_count = 0
    prior_failure_count = 0

    for order in prior_orders:

        truth = (
            evaluate_order_truth_at_time(
                order_id=order["order_id"],
                before_time=decision_time,
            )
        )

        if truth == "PAID":
            prior_success_count += 1

        elif truth == "UNPAID":
            prior_failure_count += 1

    if prior_checkout_count > 0:
        prior_success_rate = (
            prior_success_count
            / prior_checkout_count
        )
    else:
        prior_success_rate = 0.0

    return {
        "prior_checkout_count":
            prior_checkout_count,

        "prior_success_count":
            prior_success_count,

        "prior_failure_count":
            prior_failure_count,

        "prior_success_rate":
            prior_success_rate,
    }


def build_customer_order_features(
    customer_id,
    current_order_id,
    decision_time,
):
    customer = get_customer(
        customer_id
    )

    if customer is None:
        raise ValueError(
            f"Customer not found: {customer_id}"
        )

    current_order = get_order(
        current_order_id
    )

    if current_order is None:
        raise ValueError(
            f"Order not found: {current_order_id}"
        )

    prior_orders = (
        get_prior_orders_for_customer(
            customer_id=customer_id,
            before_time=decision_time,
            exclude_order_id=current_order_id,
        )
    )

    customer_tenure_days = max(
        (
            decision_time
            - customer["created_at"]
        ).days,
        0,
    )

    current_amount_minor = (
        current_order["amount_minor"]
    )

    if prior_orders:
        prior_amounts = [
            order["amount_minor"]
            for order in prior_orders
        ]

        historical_median = median(
            prior_amounts
        )

        if historical_median > 0:
            amount_ratio = (
                current_amount_minor
                / historical_median
            )
        else:
            amount_ratio = 1.0

    else:
        amount_ratio = 1.0

    return {
        "customer_tenure_days":
            customer_tenure_days,

        "current_amount_minor":
            current_amount_minor,

        "amount_ratio":
            amount_ratio,

        "contact_consent":
            customer["contact_consent"],
    }
