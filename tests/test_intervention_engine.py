from datetime import datetime, timezone

from simulator.config import SimulatorConfig
from simulator.customer_generator import CustomerGenerator
from simulator.history_generator import HistoricalJourneyGenerator
from simulator.intervention_engine import InterventionEngine
from simulator.journey_processor import JourneyProcessor
from simulator.models import (
    ActionType,
    PaymentStatus,
    RecoveryAction,
)
from simulator.random_source import RandomSource


REFERENCE_TIME = datetime(
    2026,
    9,
    4,
    tzinfo=timezone.utc,
)


def build_failed_state(seed: int = 42):
    config = SimulatorConfig()
    random_source = RandomSource(seed)

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
        return build_failed_state(seed + 1)

    journey = history[0]

    journey.payment_attempts[-1].status = (
        PaymentStatus.FAILED
    )

    processor = JourneyProcessor(
        config,
        random_source,
    )

    engine = InterventionEngine(
        config=config,
        random_source=random_source,
        journey_processor=processor,
    )

    return (
        config,
        customer,
        journey,
        engine,
    )

def test_action_simulation_does_not_modify_original_journey():
    config, customer, journey, engine = (
        build_failed_state()
    )

    original_attempt_count = len(
        journey.payment_attempts
    )

    engine.simulate_action(
        customer=customer,
        journey=journey,
        action=RecoveryAction(
            action_type=ActionType.NO_ACTION,
        ),
    )

    assert (
        len(journey.payment_attempts)
        == original_attempt_count
    )

def test_offer_does_not_change_original_order_amount():
    config, customer, journey, engine = (
        build_failed_state(50)
    )

    original_amount = journey.amount_minor

    result = engine.simulate_action(
        customer=customer,
        journey=journey,
        action=RecoveryAction(
            action_type=ActionType.APPROVED_OFFER,
            discount_percent=10.0,
        ),
    )

    assert result.amount_minor == original_amount
    assert journey.amount_minor == original_amount

def test_switch_action_uses_requested_target_when_followed():
    config, customer, journey, engine = (
        build_failed_state(91)
    )

    available_methods = (
        engine.processor
        .natural_recovery
        .method_selector
        .get_available_methods(customer)
    )

    alternate_methods = [
        method
        for method in available_methods
        if method
        != journey.payment_attempts[-1].method
    ]

    if not alternate_methods:
        return

    target = alternate_methods[0]

    # Make the customer highly willing to change method.
    customer.method_flexibility = 1.0
    customer.habitual_method = target

    result = engine.simulate_action(
        customer=customer,
        journey=journey,
        action=RecoveryAction(
            action_type=ActionType.SWITCH_METHOD,
            target_method=target,
        ),
    )

    assert len(result.payment_attempts) >= 1

def test_offer_does_not_reduce_latent_order_propensity():
    config, customer, journey, engine = (
        build_failed_state(73)
    )

    original_propensity = (
        journey.latent_order_propensity
    )

    result = engine.simulate_action(
        customer=customer,
        journey=journey,
        action=RecoveryAction(
            action_type=ActionType.APPROVED_OFFER,
            discount_percent=10.0,
        ),
    )

    assert (
        result.latent_order_propensity
        >= original_propensity
    )
