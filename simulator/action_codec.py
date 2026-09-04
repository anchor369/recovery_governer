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


def treatment_label_to_features(
    treatment: str,
) -> tuple[str, str, float]:
    """Convert a canonical treatment label into model action fields."""

    if treatment == "NO_ACTION":
        return ("NO_ACTION", "NONE", 0.0)

    if treatment == "NUDGE":
        return ("NUDGE", "NONE", 0.0)

    if treatment.startswith("OFFER_"):
        percentage = float(
            treatment.split("_", maxsplit=1)[1]
        )
        return (
            "APPROVED_OFFER",
            "NONE",
            percentage,
        )

    if treatment.startswith("SWITCH_"):
        target_method = treatment.removeprefix(
            "SWITCH_"
        )
        return (
            "SWITCH_METHOD",
            target_method,
            0.0,
        )

    raise ValueError(
        f"Unknown treatment: {treatment}"
    )
