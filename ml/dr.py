"""
Doubly-robust utilities for recovery modeling.
"""


def calculate_dr_pseudo_outcome(
    predicted_probability: float,
    observed_outcome: int,
    action_was_observed: bool,
    behavior_propensity: float,
) -> float:
    """
    Calculate one doubly-robust pseudo-outcome.

    predicted_probability:
        Outcome model prediction for the candidate action.

    observed_outcome:
        Actual historical recovery result: 0 or 1.

    action_was_observed:
        Whether this candidate action is the action that was
        actually taken historically.

    behavior_propensity:
        Probability that the historical policy assigned the
        observed action.
    """

    if behavior_propensity <= 0:
        raise ValueError(
            "Behavior propensity must be positive."
        )

    correction = 0.0

    if action_was_observed:

        residual = (
            observed_outcome
            - predicted_probability
        )

        correction = (
            residual
            / behavior_propensity
        )

    return (
        predicted_probability
        + correction
    )