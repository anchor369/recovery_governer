import pytest

from ml.dr import (
    calculate_dr_pseudo_outcome,
)


def test_unobserved_action_keeps_model_prediction():

    result = calculate_dr_pseudo_outcome(
        predicted_probability=0.60,
        observed_outcome=1,
        action_was_observed=False,
        behavior_propensity=0.20,
    )

    assert result == pytest.approx(
        0.60
    )


def test_observed_success_corrects_prediction_upward():

    result = calculate_dr_pseudo_outcome(
        predicted_probability=0.60,
        observed_outcome=1,
        action_was_observed=True,
        behavior_propensity=0.50,
    )

    assert result > 0.60


def test_observed_failure_corrects_prediction_downward():

    result = calculate_dr_pseudo_outcome(
        predicted_probability=0.60,
        observed_outcome=0,
        action_was_observed=True,
        behavior_propensity=0.50,
    )

    assert result < 0.60


def test_lower_propensity_creates_stronger_correction():

    common_action = calculate_dr_pseudo_outcome(
        predicted_probability=0.50,
        observed_outcome=1,
        action_was_observed=True,
        behavior_propensity=0.80,
    )

    rare_action = calculate_dr_pseudo_outcome(
        predicted_probability=0.50,
        observed_outcome=1,
        action_was_observed=True,
        behavior_propensity=0.20,
    )

    assert rare_action > common_action


def test_zero_propensity_is_rejected():

    with pytest.raises(
        ValueError
    ):
        calculate_dr_pseudo_outcome(
            predicted_probability=0.50,
            observed_outcome=1,
            action_was_observed=True,
            behavior_propensity=0.0,
        )