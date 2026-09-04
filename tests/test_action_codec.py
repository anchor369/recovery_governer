import pytest

from simulator.action_codec import (
    action_to_label,
)

from simulator.models import (
    ActionType,
    PaymentMethod,
    RecoveryAction,
)


def test_no_action_label():
    action = RecoveryAction(
        action_type=(
            ActionType.NO_ACTION
        ),
    )

    assert (
        action_to_label(action)
        == "NO_ACTION"
    )


def test_nudge_label():
    action = RecoveryAction(
        action_type=(
            ActionType.NUDGE
        ),
    )

    assert (
        action_to_label(action)
        == "NUDGE"
    )


def test_switch_method_label():
    action = RecoveryAction(
        action_type=(
            ActionType.SWITCH_METHOD
        ),
        target_method=(
            PaymentMethod.UPI
        ),
    )

    assert (
        action_to_label(action)
        == "SWITCH_UPI"
    )


def test_offer_label():
    action = RecoveryAction(
        action_type=(
            ActionType.APPROVED_OFFER
        ),
        discount_percent=5.0,
    )

    assert (
        action_to_label(action)
        == "OFFER_5"
    )


def test_switch_requires_target_method():
    action = RecoveryAction(
        action_type=(
            ActionType.SWITCH_METHOD
        ),
    )

    with pytest.raises(
        ValueError,
        match="requires target_method",
    ):
        action_to_label(action)


def test_offer_requires_discount():
    action = RecoveryAction(
        action_type=(
            ActionType.APPROVED_OFFER
        ),
    )

    with pytest.raises(
        ValueError,
        match="requires discount_percent",
    ):
        action_to_label(action)