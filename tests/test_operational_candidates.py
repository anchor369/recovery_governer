from types import SimpleNamespace

from backend.services.recovery_candidates import (
    build_structural_candidates,
)

from simulator.models import (
    ActionType,
    PaymentMethod,
)


def test_structural_candidates_respect_method_availability():
    state = SimpleNamespace(
        current_method=PaymentMethod.UPI,

        available_upi=True,
        available_credit_card=True,
        available_debit_card=False,
        available_netbanking=True,
    )

    candidates = build_structural_candidates(
        state
    )

    switch_methods = {
        action.target_method
        for action in candidates
        if (
            action.action_type
            == ActionType.SWITCH_METHOD
        )
    }

    assert (
        PaymentMethod.CREDIT_CARD
        in switch_methods
    )

    assert (
        PaymentMethod.NETBANKING
        in switch_methods
    )

    assert (
        PaymentMethod.DEBIT_CARD
        not in switch_methods
    )

    assert (
        PaymentMethod.UPI
        not in switch_methods
    )

def test_structural_candidates_always_include_basics_and_offers():
    state = SimpleNamespace(
        current_method=PaymentMethod.UPI,

        available_upi=True,
        available_credit_card=False,
        available_debit_card=False,
        available_netbanking=False,
    )

    candidates = build_structural_candidates(
        state
    )

    action_types = [
        action.action_type
        for action in candidates
    ]

    discounts = {
        action.discount_percent
        for action in candidates
        if (
            action.action_type
            == ActionType.APPROVED_OFFER
        )
    }

    assert (
        ActionType.NO_ACTION
        in action_types
    )

    assert (
        ActionType.NUDGE
        in action_types
    )

    assert discounts == {
        5.0,
        10.0,
    }