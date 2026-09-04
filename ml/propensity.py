"""
Propensity-weight helpers for observational recovery data.

These weights correct, approximately, for biased historical
treatment assignment.
"""

import pandas as pd


DEFAULT_MAX_IPW = 15.0


def calculate_ipw_weights(
    dataframe: pd.DataFrame,
    max_weight: float = DEFAULT_MAX_IPW,
) -> pd.Series:
    """
    Calculate clipped and normalized inverse propensity weights.

    Raw IPW:
        1 / P(observed action | state)

    Large weights are clipped for stability, then normalized so the
    average training weight equals 1.
    """

    propensity = (
        dataframe[
            "behavior_policy_probability"
        ].astype(float)
    )

    if (
        propensity <= 0
    ).any():
        raise ValueError(
            "Behavior propensity must be positive."
        )

    raw_weights = (
        1.0 / propensity
    )

    clipped_weights = (
        raw_weights.clip(
            upper=max_weight
        )
    )

    normalized_weights = (
        clipped_weights
        / clipped_weights.mean()
    )

    return normalized_weights