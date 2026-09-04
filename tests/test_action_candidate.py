from datetime import datetime, timezone

from simulator.action_candidates import (
    ActionCandidateGenerator,
)
from simulator.config import SimulatorConfig
from simulator.customer_generator import CustomerGenerator
from simulator.history_generator import HistoricalJourneyGenerator
from simulator.method_selector import PaymentMethodSelector
from simulator.models import (
    ActionType,
    PaymentStatus,
)
from simulator.random_source import RandomSource


REFERENCE_TIME = datetime(
    2026,
    9,
    4,
    tzinfo=timezone.utc,
)


def build_failed_journey():
    config = SimulatorConfig()
    random_source = RandomSource(42)

    customer = CustomerGenerator(
        config,
        random_source,
    ).generate_customer()

    history = HistoricalJourneyGenerator(
        config,
        random_source,
        REFERENCE_TIME,
    ).generate_history(customer)

    if not history:
        return build_failed_journey()

    journey = history[0]

    journey.payment_attempts[-1].status = (
        PaymentStatus.FAILED
    )

    selector = PaymentMethodSelector(
        config,
        random_source,
    )

    generator = ActionCandidateGenerator(
        config=config,
        method_selector=selector,
    )

    return customer, journey, generator


def test_failed_payment_always_has_no_action_candidate():
    customer, journey, generator = (
        build_failed_journey()
    )

    candidates = generator.generate_candidates(
        customer,
        journey,
    )

    assert any(
        candidate.action_type
        == ActionType.NO_ACTION
        for candidate in candidates
    )


def test_switch_candidate_never_targets_current_method():
    customer, journey, generator = (
        build_failed_journey()
    )

    current_method = (
        journey.payment_attempts[-1].method
    )

    candidates = generator.generate_candidates(
        customer,
        journey,
    )

    for candidate in candidates:

        if (
            candidate.action_type
            == ActionType.SWITCH_METHOD
        ):
            assert (
                candidate.target_method
                != current_method
            )


def test_uncertain_payment_has_no_recovery_candidates():
    customer, journey, generator = (
        build_failed_journey()
    )

    journey.payment_attempts[-1].status = (
        PaymentStatus.UNCERTAIN
    )

    candidates = generator.generate_candidates(
        customer,
        journey,
    )

    assert candidates == []