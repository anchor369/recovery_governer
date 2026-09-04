from datetime import datetime, timezone

from simulator.config import SimulatorConfig
from simulator.decision_state import RecoveryDecisionStateBuilder
from simulator.method_selector import PaymentMethodSelector
from simulator.models import (
    BankAccount,
    FailureCategory,
    HistoricalJourney,
    PaymentAttempt,
    PaymentMethod,
    PaymentStatus,
    SyntheticCustomer,
)
from simulator.random_source import RandomSource


def make_customer() -> SyntheticCustomer:
    return SyntheticCustomer(
        customer_id="C_TEST",
        created_at_days_ago=100,

        merchant_affinity=0.5,
        retry_persistence=0.5,
        method_flexibility=0.5,
        price_sensitivity=0.5,

        checkout_rate_per_year=4.0,
        typical_order_value_minor=100_000,

        habitual_method=PaymentMethod.UPI,
        contact_consent=True,

        bank_accounts=[
            BankAccount(
                account_id="BA_TEST",
                bank_id="BANK_TEST",
                upi_enabled=True,
                debit_card_available=False,
                netbanking_enabled=True,
            )
        ],
    )


def test_future_retry_does_not_leak_into_decision_state():
    customer = make_customer()

    prior_journey = HistoricalJourney(
        journey_id="J_PRIOR",
        order_id="O_PRIOR",
        customer_id=customer.customer_id,

        created_at=datetime(
            2026, 9, 4, 10, 0,
            tzinfo=timezone.utc,
        ),

        amount_minor=100_000,

        base_order_motivation=0.5,
        latent_order_propensity=0.5,

        initial_method=PaymentMethod.UPI,

        payment_attempts=[
            PaymentAttempt(
                payment_id="P1",
                attempt_number=1,
                method=PaymentMethod.UPI,

                attempted_at=datetime(
                    2026, 9, 4, 10, 0,
                    tzinfo=timezone.utc,
                ),

                status=PaymentStatus.FAILED,
                failure_category=(
                    FailureCategory.TECHNICAL_FAILURE
                ),
                observed_rail_health=0.6,
            ),

            PaymentAttempt(
                payment_id="P2",
                attempt_number=2,
                method=PaymentMethod.NETBANKING,

                attempted_at=datetime(
                    2026, 9, 4, 10, 30,
                    tzinfo=timezone.utc,
                ),

                status=PaymentStatus.CAPTURED,
                observed_rail_health=0.95,
            ),
        ],
    )

    current_journey = HistoricalJourney(
        journey_id="J_CURRENT",
        order_id="O_CURRENT",
        customer_id=customer.customer_id,

        created_at=datetime(
            2026, 9, 4, 10, 15,
            tzinfo=timezone.utc,
        ),

        amount_minor=120_000,

        base_order_motivation=0.5,
        latent_order_propensity=0.5,

        initial_method=PaymentMethod.UPI,

        payment_attempts=[
            PaymentAttempt(
                payment_id="P_CURRENT",
                attempt_number=1,
                method=PaymentMethod.UPI,

                attempted_at=datetime(
                    2026, 9, 4, 10, 15,
                    tzinfo=timezone.utc,
                ),

                status=PaymentStatus.FAILED,
                failure_category=(
                    FailureCategory.ISSUER_DECLINED
                ),
                observed_rail_health=0.9,
            )
        ],
    )

    random_source = RandomSource(42)

    builder = RecoveryDecisionStateBuilder(
        random_source=random_source,

        method_selector=PaymentMethodSelector(
            config=SimulatorConfig(),
            random_source=random_source,
        ),
    )

    state = builder.build(
        customer=customer,
        current_journey=current_journey,
        prior_journeys=[
            prior_journey,
        ],
    )

    assert state.prior_checkout_count == 1
    assert state.prior_success_count == 0
    assert state.prior_failure_count == 1
    assert state.prior_success_rate == 0.0

    # new method-history checks
    assert state.prior_upi_attempt_count == 1
    assert state.prior_upi_success_count == 0
    assert state.prior_upi_success_rate == 0.0

    assert state.prior_netbanking_attempt_count == 0
    assert state.prior_netbanking_success_count == 0
    assert state.prior_netbanking_success_rate == 0.0

def test_uncertain_prior_journey_is_not_counted_as_failure():
    customer = make_customer()

    prior_journey = HistoricalJourney(
        journey_id="J_UNCERTAIN",
        order_id="O_UNCERTAIN",
        customer_id=customer.customer_id,

        created_at=datetime(
            2026, 9, 4, 9, 0,
            tzinfo=timezone.utc,
        ),

        amount_minor=100_000,

        base_order_motivation=0.5,
        latent_order_propensity=0.5,

        initial_method=PaymentMethod.UPI,

        payment_attempts=[
            PaymentAttempt(
                payment_id="P_UNCERTAIN",
                attempt_number=1,
                method=PaymentMethod.UPI,

                attempted_at=datetime(
                    2026, 9, 4, 9, 0,
                    tzinfo=timezone.utc,
                ),

                status=PaymentStatus.UNCERTAIN,
                observed_rail_health=0.5,
            )
        ],
    )

    current_journey = HistoricalJourney(
        journey_id="J_CURRENT_2",
        order_id="O_CURRENT_2",
        customer_id=customer.customer_id,

        created_at=datetime(
            2026, 9, 4, 10, 0,
            tzinfo=timezone.utc,
        ),

        amount_minor=120_000,

        base_order_motivation=0.5,
        latent_order_propensity=0.5,

        initial_method=PaymentMethod.UPI,

        payment_attempts=[
            PaymentAttempt(
                payment_id="P_CURRENT_2",
                attempt_number=1,
                method=PaymentMethod.UPI,

                attempted_at=datetime(
                    2026, 9, 4, 10, 0,
                    tzinfo=timezone.utc,
                ),

                status=PaymentStatus.FAILED,
                failure_category=(
                    FailureCategory.ISSUER_DECLINED
                ),
                observed_rail_health=0.8,
            )
        ],
    )

    random_source = RandomSource(42)

    builder = RecoveryDecisionStateBuilder(
        random_source=random_source,

        method_selector=PaymentMethodSelector(
            config=SimulatorConfig(),
            random_source=random_source,
        ),
    )

    state = builder.build(
        customer=customer,
        current_journey=current_journey,
        prior_journeys=[
            prior_journey,
        ],
    )

    assert state.prior_checkout_count == 1
    assert state.prior_success_count == 0
    assert state.prior_failure_count == 0

def test_method_history_uses_only_known_resolved_attempts():
    decision_time = datetime(
        2026, 9, 4, 10, 30,
        tzinfo=timezone.utc,
    )

    prior_journey = HistoricalJourney(
        journey_id="J_METHOD_HISTORY",
        order_id="O_METHOD_HISTORY",
        customer_id="C_TEST",

        created_at=datetime(
            2026, 9, 4, 8, 0,
            tzinfo=timezone.utc,
        ),

        amount_minor=100_000,

        base_order_motivation=0.5,
        latent_order_propensity=0.5,

        initial_method=PaymentMethod.NETBANKING,

        payment_attempts=[
            PaymentAttempt(
                payment_id="P1",
                attempt_number=1,
                method=PaymentMethod.NETBANKING,

                attempted_at=datetime(
                    2026, 9, 4, 8, 30,
                    tzinfo=timezone.utc,
                ),

                status=PaymentStatus.CAPTURED,
            ),

            PaymentAttempt(
                payment_id="P2",
                attempt_number=2,
                method=PaymentMethod.NETBANKING,

                attempted_at=datetime(
                    2026, 9, 4, 9, 0,
                    tzinfo=timezone.utc,
                ),

                status=PaymentStatus.FAILED,
                failure_category=(
                    FailureCategory.TECHNICAL_FAILURE
                ),
            ),

            PaymentAttempt(
                payment_id="P3",
                attempt_number=3,
                method=PaymentMethod.NETBANKING,

                attempted_at=datetime(
                    2026, 9, 4, 10, 0,
                    tzinfo=timezone.utc,
                ),

                status=PaymentStatus.UNCERTAIN,
            ),

            PaymentAttempt(
                payment_id="P4",
                attempt_number=4,
                method=PaymentMethod.NETBANKING,

                attempted_at=datetime(
                    2026, 9, 4, 11, 0,
                    tzinfo=timezone.utc,
                ),

                status=PaymentStatus.CAPTURED,
            ),
        ],
    )

    history = (
        RecoveryDecisionStateBuilder
        ._build_method_history(
            prior_journeys=[
                prior_journey,
            ],
            decision_time=decision_time,
        )
    )

    netbanking = history[
        PaymentMethod.NETBANKING
    ]

    assert netbanking["attempt_count"] == 3
    assert netbanking["resolved_count"] == 2
    assert netbanking["success_count"] == 1
    assert netbanking["success_rate"] == 0.5

def test_observable_amount_ratio_uses_prior_order_median():
    prior_journeys = [
        HistoricalJourney(
            journey_id="J_AMOUNT_1",
            order_id="O_AMOUNT_1",
            customer_id="C_TEST",
            created_at=datetime(
                2026, 9, 1, 10, 0,
                tzinfo=timezone.utc,
            ),
            amount_minor=80_000,
            base_order_motivation=0.5,
            latent_order_propensity=0.5,
            initial_method=PaymentMethod.UPI,
            payment_attempts=[],
        ),

        HistoricalJourney(
            journey_id="J_AMOUNT_2",
            order_id="O_AMOUNT_2",
            customer_id="C_TEST",
            created_at=datetime(
                2026, 9, 2, 10, 0,
                tzinfo=timezone.utc,
            ),
            amount_minor=100_000,
            base_order_motivation=0.5,
            latent_order_propensity=0.5,
            initial_method=PaymentMethod.UPI,
            payment_attempts=[],
        ),

        HistoricalJourney(
            journey_id="J_AMOUNT_3",
            order_id="O_AMOUNT_3",
            customer_id="C_TEST",
            created_at=datetime(
                2026, 9, 3, 10, 0,
                tzinfo=timezone.utc,
            ),
            amount_minor=120_000,
            base_order_motivation=0.5,
            latent_order_propensity=0.5,
            initial_method=PaymentMethod.UPI,
            payment_attempts=[],
        ),
    ]

    ratio = (
        RecoveryDecisionStateBuilder
        ._observable_amount_ratio(
            current_amount_minor=150_000,
            prior_journeys=prior_journeys,
        )
    )

    assert ratio == 1.5

def test_observable_amount_ratio_is_neutral_without_history():
    ratio = (
        RecoveryDecisionStateBuilder
        ._observable_amount_ratio(
            current_amount_minor=150_000,
            prior_journeys=[],
        )
    )

    assert ratio == 1.0

def test_build_uses_observable_history_for_amount_ratio():
    customer = make_customer()

    prior_journey = HistoricalJourney(
        journey_id="J_AMOUNT_PRIOR",
        order_id="O_AMOUNT_PRIOR",
        customer_id=customer.customer_id,

        created_at=datetime(
            2026, 9, 4, 9, 0,
            tzinfo=timezone.utc,
        ),

        amount_minor=100_000,

        base_order_motivation=0.5,
        latent_order_propensity=0.5,

        initial_method=PaymentMethod.UPI,

        payment_attempts=[
            PaymentAttempt(
                payment_id="P_AMOUNT_PRIOR",
                attempt_number=1,
                method=PaymentMethod.UPI,

                attempted_at=datetime(
                    2026, 9, 4, 9, 0,
                    tzinfo=timezone.utc,
                ),

                status=PaymentStatus.CAPTURED,
            )
        ],
    )

    current_journey = HistoricalJourney(
        journey_id="J_AMOUNT_CURRENT",
        order_id="O_AMOUNT_CURRENT",
        customer_id=customer.customer_id,

        created_at=datetime(
            2026, 9, 4, 10, 0,
            tzinfo=timezone.utc,
        ),

        amount_minor=150_000,

        base_order_motivation=0.5,
        latent_order_propensity=0.5,

        initial_method=PaymentMethod.UPI,

        payment_attempts=[
            PaymentAttempt(
                payment_id="P_AMOUNT_CURRENT",
                attempt_number=1,
                method=PaymentMethod.UPI,

                attempted_at=datetime(
                    2026, 9, 4, 10, 0,
                    tzinfo=timezone.utc,
                ),

                status=PaymentStatus.FAILED,
                failure_category=(
                    FailureCategory.ISSUER_DECLINED
                ),
            )
        ],
    )

    random_source = RandomSource(42)

    builder = RecoveryDecisionStateBuilder(
        random_source=random_source,

        method_selector=PaymentMethodSelector(
            config=SimulatorConfig(),
            random_source=random_source,
        ),
    )

    state = builder.build(
        customer=customer,
        current_journey=current_journey,
        prior_journeys=[
            prior_journey,
        ],
    )

    assert state.amount_ratio == 1.5