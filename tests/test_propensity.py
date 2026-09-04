import pandas as pd
import pytest

from ml.propensity import (
    calculate_ipw_weights,
)


def test_lower_propensity_gets_higher_weight():

    dataframe = pd.DataFrame(
        {
            "behavior_policy_probability": [
                0.80,
                0.40,
                0.10,
            ]
        }
    )

    weights = calculate_ipw_weights(
        dataframe
    )

    assert (
        weights.iloc[2]
        > weights.iloc[1]
        > weights.iloc[0]
    )


def test_weights_are_normalized():

    dataframe = pd.DataFrame(
        {
            "behavior_policy_probability": [
                0.50,
                0.25,
                0.10,
            ]
        }
    )

    weights = calculate_ipw_weights(
        dataframe
    )

    assert weights.mean() == pytest.approx(
        1.0
    )


def test_extreme_weight_is_clipped():

    dataframe = pd.DataFrame(
        {
            "behavior_policy_probability": [
                0.50,
                0.01,
            ]
        }
    )

    weights_with_clipping = (
        calculate_ipw_weights(
            dataframe,
            max_weight=15.0,
        )
    )

    weights_without_strong_clipping = (
        calculate_ipw_weights(
            dataframe,
            max_weight=100.0,
        )
    )

    assert (
        weights_with_clipping.iloc[1]
        <
        weights_without_strong_clipping.iloc[1]
    )