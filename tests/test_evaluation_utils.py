from collections import Counter
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from policy.economics import MerchantEconomics
from scripts import evaluation_utils
from scripts.evaluation_utils import (
    collect_evaluation_states,
    evaluate_counterfactual_model,
    expected_discount_spend_minor,
    find_action,
    fixed_action_cost_minor,
    print_counterfactual_results,
)
from simulator.action_codec import action_to_label
from simulator.config import SimulatorConfig
from simulator.models import (
    ActionType,
    RecoveryAction,
)


def test_estimate_true_probability_preserves_seed_schedule(
    monkeypatch,
):
    observed_seeds = []

    def fake_branch_recovered(**kwargs):
        observed_seeds.append(kwargs["seed"])
        return kwargs["seed"] != 5_020_001

    monkeypatch.setattr(
        evaluation_utils,
        "branch_recovered",
        fake_branch_recovered,
    )

    probability = evaluation_utils.estimate_true_probability(
        config=object(),
        customer=object(),
        journey=object(),
        action=object(),
        state_index=2,
        rollouts_per_action=3,
        seed_base=5_000_000,
    )

    assert observed_seeds == [
        5_020_000,
        5_020_001,
        5_020_002,
    ]
    assert probability == pytest.approx(2 / 3)


def test_collected_states_preserve_eligible_actions_and_probabilities():
    records = collect_evaluation_states(
        config=SimulatorConfig(),
        reference_time=datetime(
            2026,
            9,
            4,
            tzinfo=timezone.utc,
        ),
        target_states=2,
        world_seed=20260905,
        include_historical_probabilities=True,
    )

    assert len(records) == 2

    for record in records:
        assert len(record) == 5
        _, _, _, eligible_actions, probabilities = record
        assert action_to_label(eligible_actions[0]) == "NO_ACTION"
        assert eligible_actions == [
            action
            for action, _ in probabilities
        ]


def test_counterfactual_metrics_match_existing_semantics():
    records = [
        {
            "true": {
                "NO_ACTION": 0.2,
                "NUDGE": 0.5,
            },
            "model": {
                "NO_ACTION": 0.3,
                "NUDGE": 0.4,
            },
        }
    ]

    results = evaluate_counterfactual_model(
        records,
        "model",
    )

    assert results["probability_mae"] == pytest.approx(0.1)
    assert results["uplift_mae"] == pytest.approx(0.2)
    assert results["uplift_correlation"] == 0.0
    assert results["best_action_accuracy"] == 1.0
    assert results["policy_value"] == 0.5
    assert results["oracle_value"] == 0.5
    assert results["no_action_value"] == 0.2
    assert results["regret"] == 0.0
    assert results["chosen_actions"]["NUDGE"] == 1


def test_counterfactual_result_format_is_preserved(capsys):
    results = {
        "probability_mae": 0.1,
        "uplift_mae": 0.2,
        "uplift_correlation": 0.3,
        "best_action_accuracy": 0.4,
        "policy_value": 0.5,
        "no_action_value": 0.6,
        "oracle_value": 0.7,
        "regret": 0.2,
        "chosen_actions": Counter(
            {"NUDGE": 2}
        ),
    }

    print_counterfactual_results("MODEL", results)
    output = capsys.readouterr().out

    assert "Probability MAE: 0.1000" in output
    assert "Best-action accuracy: 40.00%" in output
    assert "Regret vs Oracle: 20.00 pp" in output
    assert "NUDGE" in output


def test_economic_reporting_helpers_preserve_action_semantics():
    economics = MerchantEconomics()
    no_action = RecoveryAction(
        action_type=ActionType.NO_ACTION,
    )
    nudge = RecoveryAction(
        action_type=ActionType.NUDGE,
    )
    offer = RecoveryAction(
        action_type=ActionType.APPROVED_OFFER,
        discount_percent=5.0,
    )
    actions = [no_action, nudge, offer]

    assert find_action(actions, ActionType.NUDGE) == nudge
    assert fixed_action_cost_minor(no_action, economics) == 0.0
    assert (
        fixed_action_cost_minor(nudge, economics)
        == economics.nudge_cost_minor
    )
    assert expected_discount_spend_minor(
        state=SimpleNamespace(current_amount_minor=10_000),
        action=offer,
        recovery_probability=0.4,
    ) == 200.0
    assert expected_discount_spend_minor(
        state=SimpleNamespace(current_amount_minor=10_000),
        action=nudge,
        recovery_probability=0.4,
    ) == 0.0
