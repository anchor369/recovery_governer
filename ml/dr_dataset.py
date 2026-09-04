"""
Build second-stage training rows for the doubly-robust learner.

Each original historical decision row is expanded once for every
candidate treatment.
"""

import pandas as pd

from ml.dr import (
    calculate_dr_pseudo_outcome,
)


def decode_treatment(
    treatment: str,
):
    """
    Convert treatment labels into action fields used by the S-learner.
    """

    if treatment == "NO_ACTION":
        return (
            "NO_ACTION",
            "NONE",
            0.0,
        )

    if treatment == "NUDGE":
        return (
            "NUDGE",
            "NONE",
            0.0,
        )

    if treatment.startswith(
        "OFFER_"
    ):
        percentage = float(
            treatment.split(
                "_",
                maxsplit=1,
            )[1]
        )

        return (
            "APPROVED_OFFER",
            "NONE",
            percentage,
        )

    if treatment.startswith(
        "SWITCH_"
    ):
        target_method = (
            treatment.removeprefix(
                "SWITCH_"
            )
        )

        return (
            "SWITCH_METHOD",
            target_method,
            0.0,
        )

    raise ValueError(
        f"Unknown treatment: {treatment}"
    )

def treatment_is_eligible(
    row: pd.Series,
    treatment: str,
) -> bool:
    """
    Check whether a candidate treatment is structurally valid
    for this historical decision state.
    """

    if treatment == "NO_ACTION":
        return True

    if treatment == "NUDGE":
        return (
            bool(row["contact_consent"])
            and not bool(row["customer_active"])
        )

    if treatment == "OFFER_5":
        return True

    if treatment == "OFFER_10":
        return True

    if treatment == "SWITCH_UPI":
        return (
            bool(row["available_upi"])
            and row["current_method"] != "UPI"
        )

    if treatment == "SWITCH_CREDIT_CARD":
        return (
            bool(row["available_credit_card"])
            and row["current_method"]
            != "CREDIT_CARD"
        )

    if treatment == "SWITCH_DEBIT_CARD":
        return (
            bool(row["available_debit_card"])
            and row["current_method"]
            != "DEBIT_CARD"
        )

    if treatment == "SWITCH_NETBANKING":
        return (
            bool(row["available_netbanking"])
            and row["current_method"]
            != "NETBANKING"
        )

    return False

def build_dr_training_dataset(
    dataframe: pd.DataFrame,
    cross_fitted_predictions,
    treatments: list[str],
) -> pd.DataFrame:
    """
    Expand observational rows into one DR row per candidate treatment.
    """

    expanded_rows = []

    for row_position, (_, row) in enumerate(
        dataframe.iterrows()
    ):

        observed_treatment = str(
            row[
                "treatment"
            ]
        )

        observed_outcome = int(
            row[
                "recovered"
            ]
        )

        behavior_propensity = float(
            row[
                "behavior_policy_probability"
            ]
        )

        # -------------------------------------------------
        # SANITY CHECK:
        # the action that really happened historically
        # must be considered eligible.
        # -------------------------------------------------

        if not treatment_is_eligible(
            row=row,
            treatment=observed_treatment,
        ):
            raise ValueError(
                "Observed historical treatment is not eligible "
                f"for row {row_position}: {observed_treatment}"
            )

        for treatment in treatments:

            if not treatment_is_eligible(
                row=row,
                treatment=treatment,
            ):
                continue
            
            predicted_probability = float(
                cross_fitted_predictions[
                    treatment
                ][
                    row_position
                ]
            )

            action_was_observed = (
                treatment
                == observed_treatment
            )

            pseudo_outcome = (
                calculate_dr_pseudo_outcome(
                    predicted_probability=(
                        predicted_probability
                    ),
                    observed_outcome=(
                        observed_outcome
                    ),
                    action_was_observed=(
                        action_was_observed
                    ),
                    behavior_propensity=(
                        behavior_propensity
                    ),
                )
            )

            (
                action_type,
                target_method,
                discount_percent,
            ) = decode_treatment(
                treatment
            )

            expanded_row = (
                row.to_dict()
            )

            # Candidate being evaluated by the second-stage model.
            expanded_row[
                "candidate_treatment"
            ] = treatment

            expanded_row[
                "action_type"
            ] = action_type

            expanded_row[
                "target_method"
            ] = target_method

            expanded_row[
                "discount_percent"
            ] = discount_percent

            # Diagnostics.
            expanded_row[
                "first_stage_prediction"
            ] = predicted_probability

            expanded_row[
                "action_was_observed"
            ] = int(
                action_was_observed
            )

            # Training target for second-stage DR model.
            expanded_row[
                "dr_pseudo_outcome"
            ] = pseudo_outcome

            expanded_rows.append(
                expanded_row
            )

    return pd.DataFrame(
        expanded_rows
    )