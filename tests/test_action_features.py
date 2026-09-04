import pandas as pd

from ml.action_features import (
    add_candidate_features,
    add_candidate_method_history_features,
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

        "prior_upi_attempt_count": 5,
        "prior_upi_success_count": 4,
        "prior_upi_success_rate": 0.8,

        "prior_credit_card_attempt_count": 3,
        "prior_credit_card_success_count": 2,
        "prior_credit_card_success_rate": 2 / 3,

        "prior_debit_card_attempt_count": 2,
        "prior_debit_card_success_count": 1,
        "prior_debit_card_success_rate": 0.5,

        "prior_netbanking_attempt_count": 4,
        "prior_netbanking_success_count": 3,
        "prior_netbanking_success_rate": 0.75,
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

def test_candidate_method_history_uses_netbanking_history():

    row = build_base_row()

    row[
        "target_method"
    ] = "NETBANKING"

    dataframe = pd.DataFrame(
        [row]
    )

    result = (
        add_candidate_method_history_features(
            dataframe
        )
    )

    assert (
        result.iloc[0][
            "target_method_attempt_count"
        ]
        == 4
    )

    assert (
        result.iloc[0][
            "target_method_success_count"
        ]
        == 3
    )

    assert (
        result.iloc[0][
            "target_method_success_rate"
        ]
        == 0.75
    )

def test_candidate_method_history_uses_upi_history():

    row = build_base_row()

    row[
        "target_method"
    ] = "UPI"

    dataframe = pd.DataFrame(
        [row]
    )

    result = (
        add_candidate_method_history_features(
            dataframe
        )
    )

    assert (
        result.iloc[0][
            "target_method_attempt_count"
        ]
        == 5
    )

    assert (
        result.iloc[0][
            "target_method_success_count"
        ]
        == 4
    )

    assert (
        result.iloc[0][
            "target_method_success_rate"
        ]
        == 0.8
    )

def test_candidate_method_history_is_zero_without_target_method():

    row = build_base_row()

    row[
        "target_method"
    ] = "NONE"

    dataframe = pd.DataFrame(
        [row]
    )

    result = (
        add_candidate_method_history_features(
            dataframe
        )
    )

    assert (
        result.iloc[0][
            "target_method_attempt_count"
        ]
        == 0
    )

    assert (
        result.iloc[0][
            "target_method_success_count"
        ]
        == 0
    )

    assert (
        result.iloc[0][
            "target_method_success_rate"
        ]
        == 0
    )