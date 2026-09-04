from dataclasses import dataclass

from backend.data_access.payments import (
    get_order,
    get_payments_for_order_before_time,
)
from backend.services.recovery_history import (
    build_customer_order_features,
    build_prior_order_summary,
)
from backend.services.recovery_method_history import (
    build_payment_method_summary,
)
from simulator.models import (
    FailureCategory,
    PaymentMethod,
    RecoveryDecisionState,
)


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
