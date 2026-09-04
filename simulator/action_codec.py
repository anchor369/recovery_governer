"""
Canonical serialization for recovery actions.

RecoveryAction objects are used internally, while treatment labels
such as SWITCH_UPI and OFFER_5 are persisted in datasets, models,
audit tables, and evaluation outputs.

This module keeps that conversion consistent across all layers.
"""

from simulator.models import (
    ActionType,
    RecoveryAction,
)


def action_to_label(
    action: RecoveryAction,
) -> str:
    """
    Convert a RecoveryAction to its canonical persisted treatment label.

    Examples:
        NO_ACTION
        NUDGE
        SWITCH_UPI
        SWITCH_CREDIT_CARD
        OFFER_5
        OFFER_10
    """

    if (
        action.action_type
        == ActionType.SWITCH_METHOD
    ):
        if action.target_method is None:
            raise ValueError(
                "SWITCH_METHOD requires target_method."
            )

        return (
            "SWITCH_"
            + action.target_method.value
        )

    if (
        action.action_type
        == ActionType.APPROVED_OFFER
    ):
        if action.discount_percent is None:
            raise ValueError(
                "APPROVED_OFFER requires discount_percent."
            )

        return (
            "OFFER_"
            + str(
                int(
                    action.discount_percent
                )
            )
        )

    return action.action_type.value