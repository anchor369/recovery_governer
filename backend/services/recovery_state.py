from backend.services.payment_truth import (
    evaluate_order_truth_at_time,
)

from backend.data_access.payments import (
    get_customer,
    get_order,
    get_prior_orders_for_customer,
    get_payments_for_order_before_time,
    get_payment_events_for_order_before_time,
)

from dataclasses import dataclass

from simulator.models import (
    FailureCategory,
    PaymentMethod,
    RecoveryDecisionState,
)

from statistics import median

@dataclass(frozen=True)
class RuntimeRecoverySignals:
    available_upi: bool
    available_credit_card: bool
    available_debit_card: bool
    available_netbanking: bool

    observed_rail_health: float
    customer_active: bool

KNOWN_FAILURE_CATEGORIES = {
    "USER_CANCELLED",
    "AUTHENTICATION_FAILURE",
    "INSUFFICIENT_FUNDS",
    "LIMIT_EXCEEDED",
    "INSTRUMENT_UNAVAILABLE",
    "RISK_DECLINED",
    "ISSUER_DECLINED",
    "BANK_OR_PROVIDER_UNAVAILABLE",
    "TECHNICAL_FAILURE",
    "OTHER_CONFIRMED_FAILURE",
}

def normalize_failure_category(
    failure_reason,
):
    if failure_reason is None:
        return "OTHER_CONFIRMED_FAILURE"

    normalized = str(
        failure_reason
    ).strip().upper()

    if normalized in KNOWN_FAILURE_CATEGORIES:
        return normalized

    return "OTHER_CONFIRMED_FAILURE"


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

def build_current_payment_features(
    current_order_id,
    decision_time,
):
    payments = (
        get_payments_for_order_before_time(
            order_id=current_order_id,
            before_time=decision_time,
        )
    )

    if not payments:
        raise ValueError(
            "No payment attempts existed "
            f"for Order {current_order_id} "
            "before decision time."
        )

    current_payment = payments[-1]

    current_method = (
        current_payment["method"]
        .strip()
        .upper()
    )

    failure_category = (
        normalize_failure_category(
            current_payment[
                "failure_reason"
            ]
        )
    )

    attempt_count = len(
        payments
    )

    return {
        "current_method":
            current_method,

        "failure_category":
            failure_category,

        "attempt_count":
            attempt_count,
    }

def build_recovery_decision_state(
    current_order_id,
    decision_time,
    runtime_signals,
):
    current_order = get_order(
        current_order_id
    )

    if current_order is None:
        raise ValueError(
            f"Order not found: {current_order_id}"
        )

    customer_id = current_order[
        "customer_id"
    ]

    prior_summary = (
        build_prior_order_summary(
            customer_id=customer_id,
            current_order_id=current_order_id,
            decision_time=decision_time,
        )
    )

    customer_order_features = (
        build_customer_order_features(
            customer_id=customer_id,
            current_order_id=current_order_id,
            decision_time=decision_time,
        )
    )

    method_summary = (
        build_payment_method_summary(
            customer_id=customer_id,
            current_order_id=current_order_id,
            decision_time=decision_time,
        )
    )

    current_payment_features = (
        build_current_payment_features(
            current_order_id=current_order_id,
            decision_time=decision_time,
        )
    )

    if not (
        0.0
        <= runtime_signals.observed_rail_health
        <= 1.0
    ):
        raise ValueError(
            "observed_rail_health "
            "must be between 0 and 1."
        )

    return RecoveryDecisionState(
        customer_tenure_days=(
            customer_order_features[
                "customer_tenure_days"
            ]
        ),

        prior_checkout_count=(
            prior_summary[
                "prior_checkout_count"
            ]
        ),

        prior_success_count=(
            prior_summary[
                "prior_success_count"
            ]
        ),

        prior_failure_count=(
            prior_summary[
                "prior_failure_count"
            ]
        ),

        prior_success_rate=(
            prior_summary[
                "prior_success_rate"
            ]
        ),

        prior_upi_count=(
            method_summary[
                "prior_upi_count"
            ]
        ),

        prior_credit_card_count=(
            method_summary[
                "prior_credit_card_count"
            ]
        ),

        prior_debit_card_count=(
            method_summary[
                "prior_debit_card_count"
            ]
        ),

        prior_netbanking_count=(
            method_summary[
                "prior_netbanking_count"
            ]
        ),

        prior_upi_attempt_count=(
            method_summary[
                "prior_upi_attempt_count"
            ]
        ),

        prior_upi_success_count=(
            method_summary[
                "prior_upi_success_count"
            ]
        ),

        prior_upi_success_rate=(
            method_summary[
                "prior_upi_success_rate"
            ]
        ),

        prior_credit_card_attempt_count=(
            method_summary[
                "prior_credit_card_attempt_count"
            ]
        ),

        prior_credit_card_success_count=(
            method_summary[
                "prior_credit_card_success_count"
            ]
        ),

        prior_credit_card_success_rate=(
            method_summary[
                "prior_credit_card_success_rate"
            ]
        ),

        prior_debit_card_attempt_count=(
            method_summary[
                "prior_debit_card_attempt_count"
            ]
        ),

        prior_debit_card_success_count=(
            method_summary[
                "prior_debit_card_success_count"
            ]
        ),

        prior_debit_card_success_rate=(
            method_summary[
                "prior_debit_card_success_rate"
            ]
        ),

        prior_netbanking_attempt_count=(
            method_summary[
                "prior_netbanking_attempt_count"
            ]
        ),

        prior_netbanking_success_count=(
            method_summary[
                "prior_netbanking_success_count"
            ]
        ),

        prior_netbanking_success_rate=(
            method_summary[
                "prior_netbanking_success_rate"
            ]
        ),

        available_upi=(
            runtime_signals.available_upi
        ),

        available_credit_card=(
            runtime_signals.available_credit_card
        ),

        available_debit_card=(
            runtime_signals.available_debit_card
        ),

        available_netbanking=(
            runtime_signals.available_netbanking
        ),

        current_amount_minor=(
            customer_order_features[
                "current_amount_minor"
            ]
        ),

        amount_ratio=(
            customer_order_features[
                "amount_ratio"
            ]
        ),

        current_method=PaymentMethod(
            current_payment_features[
                "current_method"
            ]
        ),

        failure_category=FailureCategory(
            current_payment_features[
                "failure_category"
            ]
        ),

        attempt_count=(
            current_payment_features[
                "attempt_count"
            ]
        ),

        observed_rail_health=(
            runtime_signals.observed_rail_health
        ),

        contact_consent=(
            customer_order_features[
                "contact_consent"
            ]
        ),

        customer_active=(
            runtime_signals.customer_active
        ),
    )