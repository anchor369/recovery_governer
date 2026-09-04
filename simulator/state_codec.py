"""
Canonical serialization of RecoveryDecisionState.

The same observable state representation is used when:
- generating historical ML data,
- running counterfactual evaluation,
- running feature experiments.

Keeping this mapping in one place prevents train/evaluation drift.
"""

from simulator.models import (
    RecoveryDecisionState,
)


def decision_state_to_model_row(
    state: RecoveryDecisionState,
) -> dict[str, object]:
    """
    Convert an observable RecoveryDecisionState into
    the flat representation consumed by ML pipelines.
    """

    return {
        "customer_tenure_days":
            state.customer_tenure_days,

        "prior_checkout_count":
            state.prior_checkout_count,

        "prior_success_count":
            state.prior_success_count,

        "prior_failure_count":
            state.prior_failure_count,

        "prior_success_rate":
            state.prior_success_rate,

        "prior_upi_count":
            state.prior_upi_count,

        "prior_credit_card_count":
            state.prior_credit_card_count,

        "prior_debit_card_count":
            state.prior_debit_card_count,

        "prior_netbanking_count":
            state.prior_netbanking_count,

        "prior_upi_attempt_count":
            state.prior_upi_attempt_count,

        "prior_upi_success_count":
            state.prior_upi_success_count,

        "prior_upi_success_rate":
            state.prior_upi_success_rate,

        "prior_credit_card_attempt_count":
            state.prior_credit_card_attempt_count,

        "prior_credit_card_success_count":
            state.prior_credit_card_success_count,

        "prior_credit_card_success_rate":
            state.prior_credit_card_success_rate,

        "prior_debit_card_attempt_count":
            state.prior_debit_card_attempt_count,

        "prior_debit_card_success_count":
            state.prior_debit_card_success_count,

        "prior_debit_card_success_rate":
            state.prior_debit_card_success_rate,

        "prior_netbanking_attempt_count":
            state.prior_netbanking_attempt_count,

        "prior_netbanking_success_count":
            state.prior_netbanking_success_count,

        "prior_netbanking_success_rate":
            state.prior_netbanking_success_rate,

        "available_upi":
            int(state.available_upi),

        "available_credit_card":
            int(state.available_credit_card),

        "available_debit_card":
            int(state.available_debit_card),

        "available_netbanking":
            int(state.available_netbanking),

        "current_amount_minor":
            state.current_amount_minor,

        "amount_ratio":
            state.amount_ratio,

        "current_method":
            state.current_method.value,

        "failure_category":
            state.failure_category.value,

        "attempt_count":
            state.attempt_count,

        "observed_rail_health":
            state.observed_rail_health,

        "contact_consent":
            int(state.contact_consent),

        "customer_active":
            int(state.customer_active),
    }