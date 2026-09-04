import numpy as np
import pandas as pd
import pytest

from ml.dr_dataset import (
    build_dr_training_dataset,
)


def build_test_dataframe():
    """
    One valid historical NUDGE example.

    NUDGE is eligible because:
    - contact consent exists
    - customer is not currently active
    """

    return pd.DataFrame(
        [
            {
                "customer_id": "C1",

                "treatment": "NUDGE",
                "recovered": 1,

                "behavior_policy_probability": 0.20,

                "contact_consent": True,
                "customer_active": False,

                "available_upi": True,
                "available_credit_card": True,
                "available_debit_card": True,
                "available_netbanking": True,

                "current_method": "UPI",
            }
        ]
    )


def build_predictions():

    return {
        "NO_ACTION": np.array(
            [0.50]
        ),

        "NUDGE": np.array(
            [0.60]
        ),
    }


def test_one_original_row_expands_to_all_treatments():

    dataframe = (
        build_test_dataframe()
    )

    treatments = [
        "NO_ACTION",
        "NUDGE",
    ]

    predictions = (
        build_predictions()
    )

    result = (
        build_dr_training_dataset(
            dataframe=dataframe,
            cross_fitted_predictions=(
                predictions
            ),
            treatments=treatments,
        )
    )

    assert len(result) == 2


def test_unobserved_action_keeps_first_stage_prediction():

    dataframe = (
        build_test_dataframe()
    )

    treatments = [
        "NO_ACTION",
        "NUDGE",
    ]

    predictions = (
        build_predictions()
    )

    result = (
        build_dr_training_dataset(
            dataframe=dataframe,
            cross_fitted_predictions=(
                predictions
            ),
            treatments=treatments,
        )
    )

    no_action_row = result[
        result[
            "candidate_treatment"
        ]
        == "NO_ACTION"
    ].iloc[0]

    assert (
        no_action_row[
            "dr_pseudo_outcome"
        ]
        == pytest.approx(
            0.50
        )
    )

    assert (
        no_action_row[
            "action_was_observed"
        ]
        == 0
    )


def test_observed_action_receives_dr_correction():

    dataframe = (
        build_test_dataframe()
    )

    treatments = [
        "NO_ACTION",
        "NUDGE",
    ]

    predictions = (
        build_predictions()
    )

    result = (
        build_dr_training_dataset(
            dataframe=dataframe,
            cross_fitted_predictions=(
                predictions
            ),
            treatments=treatments,
        )
    )

    nudge_row = result[
        result[
            "candidate_treatment"
        ]
        == "NUDGE"
    ].iloc[0]

    expected = (
        0.60
        + (
            1.0 - 0.60
        )
        / 0.20
    )

    assert (
        nudge_row[
            "dr_pseudo_outcome"
        ]
        == pytest.approx(
            expected
        )
    )

    assert (
        nudge_row[
            "action_was_observed"
        ]
        == 1
    )