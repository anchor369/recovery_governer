from simulator.models import (
    FailureCategory,
    PaymentMethod,
    RecoveryDecisionState,
)

from simulator.state_codec import (
    decision_state_to_model_row,
)


def test_decision_state_to_model_row():
    state = RecoveryDecisionState(
        customer_tenure_days=120,

        prior_checkout_count=5,
        prior_success_count=3,
        prior_failure_count=1,
        prior_success_rate=0.6,

        prior_upi_count=2,
        prior_credit_card_count=1,
        prior_debit_card_count=1,
        prior_netbanking_count=1,

        prior_upi_attempt_count=4,
        prior_upi_success_count=3,
        prior_upi_success_rate=0.75,

        prior_credit_card_attempt_count=2,
        prior_credit_card_success_count=1,
        prior_credit_card_success_rate=0.5,

        prior_debit_card_attempt_count=1,
        prior_debit_card_success_count=1,
        prior_debit_card_success_rate=1.0,

        prior_netbanking_attempt_count=3,
        prior_netbanking_success_count=1,
        prior_netbanking_success_rate=1 / 3,

        available_upi=True,
        available_credit_card=False,
        available_debit_card=True,
        available_netbanking=True,

        current_amount_minor=150_000,
        amount_ratio=1.5,

        current_method=(
            PaymentMethod.NETBANKING
        ),

        failure_category=(
            FailureCategory.TECHNICAL_FAILURE
        ),

        attempt_count=2,

        observed_rail_health=0.8,

        contact_consent=True,
        customer_active=False,
    )

    row = (
        decision_state_to_model_row(
            state
        )
    )

    assert len(row) == 33

    assert (
        row["customer_tenure_days"]
        == 120
    )

    assert (
        row["prior_upi_success_count"]
        == 3
    )

    assert (
        row["available_upi"]
        == 1
    )

    assert (
        row["available_credit_card"]
        == 0
    )

    assert (
        row["current_method"]
        == "NETBANKING"
    )

    assert (
        row["failure_category"]
        == "TECHNICAL_FAILURE"
    )

    assert (
        row["contact_consent"]
        == 1
    )

    assert (
        row["customer_active"]
        == 0
    )