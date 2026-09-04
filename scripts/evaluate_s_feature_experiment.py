from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd

from simulator.config import SimulatorConfig
from simulator.action_codec import (
    action_to_label,
)
from simulator.state_codec import (
    decision_state_to_model_row,
)
from scripts.evaluation_utils import (
    collect_evaluation_states,
    estimate_true_probability,
    evaluate_counterfactual_model,
    print_counterfactual_results,
)


REFERENCE_TIME = datetime(
    2026,
    9,
    4,
    tzinfo=timezone.utc,
)

EVALUATION_STATES = 200
ROLLOUTS_PER_ACTION = 40


BASELINE_S_MODEL_PATH = Path(
    "models/s_learner_corrected_baseline.joblib"
)

METHOD_HISTORY_S_MODEL_PATH = Path(
    "models/s_learner_method_history.joblib"
)

CANDIDATE_METHOD_S_MODEL_PATH = Path(
    "models/s_learner_candidate_method_history.joblib"
)


config = SimulatorConfig()


baseline_s_learner = joblib.load(
    BASELINE_S_MODEL_PATH
)

method_history_s_learner = joblib.load(
    METHOD_HISTORY_S_MODEL_PATH
)

candidate_method_s_learner = joblib.load(
    CANDIDATE_METHOD_S_MODEL_PATH
)

print()
print(
    "BUILDING S-LEARNER FEATURE EXPERIMENT"
)
print(
    "====================================="
)

evaluation_states = (
    collect_evaluation_states(
        config=config,
        reference_time=REFERENCE_TIME,
        target_states=EVALUATION_STATES,
        world_seed=20260904,
    )
)

print(
    "States:",
    len(evaluation_states),
)

print(
    "Rollouts per eligible action:",
    ROLLOUTS_PER_ACTION,
)


truth_records = []


for state_index, (
    customer,
    journey,
    state,
    eligible_actions,
) in enumerate(
    evaluation_states
):

    if (
        state_index + 1
    ) % 25 == 0:
        print(
            "Evaluated states:",
            state_index + 1,
        )

    row_frame = pd.DataFrame(
        [
            decision_state_to_model_row(
                state
            )
        ]
    )

    true_probabilities = {}

    baseline_predictions = {}

    method_history_predictions = {}

    candidate_method_predictions = {}


    for action in eligible_actions:

        label = action_to_label(
            action
        )

        true_probability = (
            estimate_true_probability(
                config=config,
                customer=customer,
                journey=journey,
                action=action,
                state_index=state_index,
                rollouts_per_action=ROLLOUTS_PER_ACTION,
                seed_base=5_000_000,
            )
        )

        true_probabilities[
            label
        ] = true_probability


        baseline_probability = float(
            baseline_s_learner
            .predict_treatment(
                dataframe=row_frame,
                treatment=label,
            )[0]
        )

        baseline_predictions[
            label
        ] = baseline_probability


        method_history_probability = float(
            method_history_s_learner
            .predict_treatment(
                dataframe=row_frame,
                treatment=label,
            )[0]
        )

        method_history_predictions[
            label
        ] = (
            method_history_probability
        )

        candidate_method_probability = float(
            candidate_method_s_learner
            .predict_treatment(
                dataframe=row_frame,
                treatment=label,
            )[0]
        )

        candidate_method_predictions[
            label
        ] = candidate_method_probability

    truth_records.append(
        {
            "true":
                true_probabilities,

            "baseline_s":
                baseline_predictions,

            "method_history_s":
                method_history_predictions,

            "candidate_method_s":
                candidate_method_predictions,
        }
    )


baseline_results = evaluate_counterfactual_model(
    truth_records,
    "baseline_s",
)

method_history_results = (
    evaluate_counterfactual_model(
        truth_records,
        "method_history_s",
    )
)

candidate_method_results = evaluate_counterfactual_model(
    truth_records,
    "candidate_method_s",
)

print()
print(
    "COUNTERFACTUAL S-LEARNER COMPARISON"
)
print(
    "==================================="
)


print_counterfactual_results(
    "CORRECTED BASELINE S-LEARNER",
    baseline_results,
)

print_counterfactual_results(
    "S-LEARNER + METHOD HISTORY",
    method_history_results,
)

print_counterfactual_results(
    "S-LEARNER + CANDIDATE METHOD HISTORY",
    candidate_method_results,
)


print()
print(
    "DELTA: METHOD HISTORY - BASELINE"
)
print(
    "--------------------------------"
)

print(
    "Probability MAE:",
    (
        f"{method_history_results['probability_mae'] - baseline_results['probability_mae']:+.4f}"
    ),
)

print(
    "Uplift MAE:",
    (
        f"{method_history_results['uplift_mae'] - baseline_results['uplift_mae']:+.4f}"
    ),
)

print(
    "Uplift correlation:",
    (
        f"{method_history_results['uplift_correlation'] - baseline_results['uplift_correlation']:+.4f}"
    ),
)

print(
    "Best-action accuracy:",
    (
        f"{(
            method_history_results['best_action_accuracy']
            - baseline_results['best_action_accuracy']
        ) * 100:+.2f} pp"
    ),
)

print(
    "Policy recovery:",
    (
        f"{(
            method_history_results['policy_value']
            - baseline_results['policy_value']
        ) * 100:+.2f} pp"
    ),
)

print(
    "Regret:",
    (
        f"{(
            method_history_results['regret']
            - baseline_results['regret']
        ) * 100:+.2f} pp"
    ),
)

print()
print(
    "DELTA: CANDIDATE METHOD HISTORY - BASELINE"
)
print(
    "------------------------------------------"
)

print(
    "Probability MAE:",
    (
        f"{candidate_method_results['probability_mae'] - baseline_results['probability_mae']:+.4f}"
    ),
)

print(
    "Uplift MAE:",
    (
        f"{candidate_method_results['uplift_mae'] - baseline_results['uplift_mae']:+.4f}"
    ),
)

print(
    "Uplift correlation:",
    (
        f"{candidate_method_results['uplift_correlation'] - baseline_results['uplift_correlation']:+.4f}"
    ),
)

print(
    "Best-action accuracy:",
    (
        f"{(
            candidate_method_results['best_action_accuracy']
            - baseline_results['best_action_accuracy']
        ) * 100:+.2f} pp"
    ),
)

print(
    "Policy recovery:",
    (
        f"{(
            candidate_method_results['policy_value']
            - baseline_results['policy_value']
        ) * 100:+.2f} pp"
    ),
)

print(
    "Regret:",
    (
        f"{(
            candidate_method_results['regret']
            - baseline_results['regret']
        ) * 100:+.2f} pp"
    ),
)
