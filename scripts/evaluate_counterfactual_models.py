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

# Start reasonably small so we can inspect quickly.
EVALUATION_STATES = 200
ROLLOUTS_PER_ACTION = 40

T_MODEL_PATH = Path(
    "models/t_learner.joblib"
)

S_MODEL_PATH = Path(
    "models/s_learner.joblib"
)

IPW_S_MODEL_PATH = Path(
    "models/ipw_s_learner.joblib"
)

DR_MODEL_PATH = Path(
    "models/dr_learner.joblib"
)

config = SimulatorConfig()

t_learner = joblib.load(
    T_MODEL_PATH
)

s_learner = joblib.load(
    S_MODEL_PATH
)

ipw_s_learner = joblib.load(
    IPW_S_MODEL_PATH
)

dr_learner = joblib.load(
    DR_MODEL_PATH
)

print()
print("BUILDING COUNTERFACTUAL TRUTH SET")
print("---------------------------------")

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
            decision_state_to_model_row(state)
        ]
    )

    true_probabilities = {}
    t_predictions = {}
    s_predictions = {}
    ipw_s_predictions = {}
    dr_predictions = {}

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

        if label in t_learner.models:

            t_probability = float(
                t_learner
                .predict_probability(
                    dataframe=row_frame,
                    treatment=label,
                )[0]
            )

            t_predictions[
                label
            ] = t_probability

        s_probability = float(
            s_learner
            .predict_treatment(
                dataframe=row_frame,
                treatment=label,
            )[0]
        )

        s_predictions[
            label
        ] = s_probability

        ipw_s_probability = float(
            ipw_s_learner
            .predict_treatment(
                dataframe=row_frame,
                treatment=label,
            )[0]
        )

        ipw_s_predictions[
            label
        ] = ipw_s_probability

        dr_probability = float(
            dr_learner
            .predict_treatment(
                dataframe=row_frame,
                treatment=label,
            )[0]
        )

        dr_predictions[
            label
        ] = dr_probability

    truth_records.append(
        {
            "true": true_probabilities,
            "t": t_predictions,
            "s": s_predictions,
            "ipw_s": ipw_s_predictions,
            "dr": dr_predictions,
        }
    )


t_results = evaluate_counterfactual_model(
    truth_records,
    "t",
)

s_results = evaluate_counterfactual_model(
    truth_records,
    "s",
)

ipw_s_results = evaluate_counterfactual_model(
    truth_records,
    "ipw_s",
)

dr_results = evaluate_counterfactual_model(
    truth_records,
    "dr",
)

print()
print("COUNTERFACTUAL MODEL EVALUATION")
print("===============================")

print_counterfactual_results(
    "T-LEARNER",
    t_results,
)

print_counterfactual_results(
    "POOLED S-LEARNER",
    s_results,
)

print_counterfactual_results(
    "IPW POOLED S-LEARNER",
    ipw_s_results,
)

print_counterfactual_results(
    "DOUBLY ROBUST LEARNER",
    dr_results,
)
