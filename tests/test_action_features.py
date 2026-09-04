import pandas as pd

from ml.action_features import (
    add_candidate_features,
)


def build_base_row():

    return {
        "prior_upi_count": 6,
        "prior_credit_card_count": 3,
        "prior_debit_card_count": 1,
        "prior_netbanking_count": 0,

        "available_upi": True,
        "available_credit_card": True,
        "available_debit_card": True,
        "available_netbanking": False,
    }


def test_credit_card_target_features():

    row = build_base_row()

    row[
        "target_method"
    ] = "CREDIT_CARD"

    dataframe = pd.DataFrame(
        [row]
    )

    result = add_candidate_features(
        dataframe
    )

    assert (
        result.iloc[0][
            "target_prior_usage_count"
        ]
        == 3
    )

    assert (
        result.iloc[0][
            "target_prior_usage_share"
        ]
        == 0.30
    )

    assert (
        result.iloc[0][
            "target_available"
        ]
        == 1
    )


def test_netbanking_target_features():

    row = build_base_row()

    row[
        "target_method"
    ] = "NETBANKING"

    dataframe = pd.DataFrame(
        [row]
    )

    result = add_candidate_features(
        dataframe
    )

    assert (
        result.iloc[0][
            "target_prior_usage_count"
        ]
        == 0
    )

    assert (
        result.iloc[0][
            "target_prior_usage_share"
        ]
        == 0
    )

    assert (
        result.iloc[0][
            "target_available"
        ]
        == 0
    )


def test_non_switch_action_has_zero_target_features():

    row = build_base_row()

    row[
        "target_method"
    ] = "NONE"

    dataframe = pd.DataFrame(
        [row]
    )

    result = add_candidate_features(
        dataframe
    )

    assert (
        result.iloc[0][
            "target_prior_usage_count"
        ]
        == 0
    )

    assert (
        result.iloc[0][
            "target_prior_usage_share"
        ]
        == 0
    )

    assert (
        result.iloc[0][
            "target_available"
        ]
        == 0
    )