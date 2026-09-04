import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np

from policy.economics import (
    MerchantEconomics,
    expected_merchant_value_minor,
)
from policy.governor import RecoveryGovernor
from simulator.config import SimulatorConfig
from simulator.models import (
    ActionType,
)

from simulator.action_codec import (
    action_to_label,
)
from scripts.evaluation_utils import (
    collect_evaluation_states,
    estimate_true_probability,
    expected_discount_spend_minor,
    find_action,
    fixed_action_cost_minor,
)

REFERENCE_TIME = datetime(
    2026,
    9,
    4,
    tzinfo=timezone.utc,
)

EVALUATION_STATES = 250
ROLLOUTS_PER_ACTION = 50

MODEL_PATH = Path(
    "models/s_learner.joblib"
)

DETAIL_PATH = Path(
    "data/governor_evaluation.csv"
)

SUMMARY_PATH = Path(
    "data/economic_benchmark_summary.csv"
)


config = SimulatorConfig()

economics = MerchantEconomics()

learner = joblib.load(
    MODEL_PATH
)

governor = RecoveryGovernor(
    learner=learner,
    economics=economics,
    max_payment_attempts=(
        config.max_payment_attempts
    ),
)

print()
print("BUILDING ECONOMIC EVALUATION SET")
print("--------------------------------")

evaluation_states = collect_evaluation_states(
    config=config,
    reference_time=REFERENCE_TIME,
    target_states=EVALUATION_STATES,
    world_seed=20260905,
    include_historical_probabilities=True,
)

print(
    "States:",
    len(evaluation_states),
)

print(
    "Rollouts per eligible action:",
    ROLLOUTS_PER_ACTION,
)


policy_names = [
    "NO_ACTION",
    "BLANKET_NUDGE",
    "RULE_BASED",
    "S_LEARNER_RECOVERY_MAX",
    "ECONOMIC_GOVERNOR",
    "ECONOMIC_ORACLE",
]


metrics = {
    name: {
        "recovery_probability": [],
        "merchant_value_minor": [],
        "discount_spend_minor": [],
        "action_cost_minor": [],
        "interventions": 0,
        "unnecessary_interventions": 0,
        "actions": Counter(),
    }
    for name in policy_names
}


detail_rows = []


for state_index, (
    customer,
    journey,
    state,
    eligible_actions,
    historical_probabilities,
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

    true_probabilities = {}

    for action in eligible_actions:

        label = action_to_label(
            action
        )

        true_probabilities[
            label
        ] = (
            estimate_true_probability(
                config=config,
                customer=customer,
                journey=journey,
                action=action,
                state_index=state_index,
                rollouts_per_action=ROLLOUTS_PER_ACTION,
                seed_base=8_000_000,
            )
        )

    no_action = find_action(
        eligible_actions,
        ActionType.NO_ACTION,
    )

    no_action_label = action_to_label(
        no_action
    )

    no_action_probability = (
        true_probabilities[
            no_action_label
        ]
    )

    no_action_true_value = (
        expected_merchant_value_minor(
            state=state,
            action=no_action,
            recovery_probability=(
                no_action_probability
            ),
            economics=economics,
        )
    )

    #
    # POLICY 1 — NO ACTION
    #
    selected_actions = {
        "NO_ACTION":
            no_action,
    }

    #
    # POLICY 2 — BLANKET NUDGE
    #
    nudge = find_action(
        eligible_actions,
        ActionType.NUDGE,
    )

    selected_actions[
        "BLANKET_NUDGE"
    ] = (
        nudge
        if nudge is not None
        else no_action
    )

    #
    # POLICY 3 — RULE BASED
    #
    rule_based_action = max(
        historical_probabilities,
        key=lambda pair:
            pair[1],
    )[0]

    selected_actions[
        "RULE_BASED"
    ] = rule_based_action

    #
    # POLICY 4 — S-LEARNER RECOVERY MAX
    #
    state_frame = (
        governor._state_frame(
            state
        )
    )

    predicted_recovery = {}

    for action in eligible_actions:

        label = action_to_label(
            action
        )

        predicted_recovery[
            label
        ] = float(
            learner.predict_treatment(
                dataframe=state_frame,
                treatment=label,
            )[0]
        )

    recovery_max_action = max(
        eligible_actions,
        key=lambda action:
            predicted_recovery[
                action_to_label(action)
            ],
    )

    selected_actions[
        "S_LEARNER_RECOVERY_MAX"
    ] = recovery_max_action

    #
    # POLICY 5 — ECONOMIC GOVERNOR
    #
    governor_decision = (
        governor.decide(
            state=state,
            candidates=eligible_actions,
        )
    )

    selected_actions[
        "ECONOMIC_GOVERNOR"
    ] = (
        governor_decision
        .chosen_action
    )

    #
    # POLICY 6 — TRUE ECONOMIC ORACLE
    #
    true_action_values = {}

    for action in eligible_actions:

        label = action_to_label(
            action
        )

        true_action_values[
            label
        ] = (
            expected_merchant_value_minor(
                state=state,
                action=action,
                recovery_probability=(
                    true_probabilities[
                        label
                    ]
                ),
                economics=economics,
            )
        )

    economic_oracle_action = max(
        eligible_actions,
        key=lambda action:
            true_action_values[
                action_to_label(action)
            ],
    )

    selected_actions[
        "ECONOMIC_ORACLE"
    ] = economic_oracle_action

    detail_row = {
        "state_id":
            state_index + 1,

        "failure_category":
            state.failure_category.value,

        "current_method":
            state.current_method.value,

        "amount_minor":
            state.current_amount_minor,

        "no_action_probability":
            no_action_probability,
    }

    for policy_name, action in (
        selected_actions.items()
    ):

        label = action_to_label(
            action
        )

        true_probability = (
            true_probabilities[
                label
            ]
        )

        true_value = (
            expected_merchant_value_minor(
                state=state,
                action=action,
                recovery_probability=(
                    true_probability
                ),
                economics=economics,
            )
        )

        discount_spend = (
            expected_discount_spend_minor(
                state=state,
                action=action,
                recovery_probability=(
                    true_probability
                ),
            )
        )

        action_cost = (
            fixed_action_cost_minor(
                action,
                economics,
            )
        )

        intervention = (
            action.action_type
            != ActionType.NO_ACTION
        )

        unnecessary = (
            intervention
            and true_value
            <= no_action_true_value
        )

        policy_metrics = (
            metrics[
                policy_name
            ]
        )

        policy_metrics[
            "recovery_probability"
        ].append(
            true_probability
        )

        policy_metrics[
            "merchant_value_minor"
        ].append(
            true_value
        )

        policy_metrics[
            "discount_spend_minor"
        ].append(
            discount_spend
        )

        policy_metrics[
            "action_cost_minor"
        ].append(
            action_cost
        )

        policy_metrics[
            "interventions"
        ] += int(
            intervention
        )

        policy_metrics[
            "unnecessary_interventions"
        ] += int(
            unnecessary
        )

        policy_metrics[
            "actions"
        ][
            label
        ] += 1

        detail_row[
            f"{policy_name}_action"
        ] = label

        detail_row[
            f"{policy_name}_recovery_probability"
        ] = true_probability

        detail_row[
            f"{policy_name}_merchant_value_minor"
        ] = true_value

    detail_rows.append(
        detail_row
    )


baseline_recovery = float(
    np.mean(
        metrics[
            "NO_ACTION"
        ][
            "recovery_probability"
        ]
    )
)

baseline_value = float(
    np.mean(
        metrics[
            "NO_ACTION"
        ][
            "merchant_value_minor"
        ]
    )
)

oracle_value = float(
    np.mean(
        metrics[
            "ECONOMIC_ORACLE"
        ][
            "merchant_value_minor"
        ]
    )
)


summary_rows = []


print()
print("ECONOMIC RECOVERY BENCHMARK")
print("===========================")


for policy_name in policy_names:

    result = metrics[
        policy_name
    ]

    recovery = float(
        np.mean(
            result[
                "recovery_probability"
            ]
        )
    )

    merchant_value = float(
        np.mean(
            result[
                "merchant_value_minor"
            ]
        )
    )

    discount_spend = float(
        np.mean(
            result[
                "discount_spend_minor"
            ]
        )
    )

    action_cost = float(
        np.mean(
            result[
                "action_cost_minor"
            ]
        )
    )

    intervention_rate = (
        result[
            "interventions"
        ]
        / EVALUATION_STATES
    )

    if (
        result[
            "interventions"
        ]
        > 0
    ):

        unnecessary_rate = (
            result[
                "unnecessary_interventions"
            ]
            / result[
                "interventions"
            ]
        )

    else:
        unnecessary_rate = 0.0

    incremental_recovery_pp = (
        recovery
        - baseline_recovery
    ) * 100.0

    incremental_value_minor = (
        merchant_value
        - baseline_value
    )

    regret_minor = (
        oracle_value
        - merchant_value
    )

    print()
    print(policy_name)
    print(
        "-" * len(policy_name)
    )

    print(
        "Recovery:",
        f"{recovery * 100:.2f}%",
    )

    print(
        "Incremental recovery:",
        f"{incremental_recovery_pp:+.2f} pp",
    )

    print(
        "Intervention rate:",
        f"{intervention_rate * 100:.2f}%",
    )

    print(
        "Unnecessary interventions:",
        f"{unnecessary_rate * 100:.2f}%",
    )

    print(
        "Expected merchant value / failed order:",
        f"₹{merchant_value / 100:.2f}",
    )

    print(
        "Net incremental value / failed order:",
        f"₹{incremental_value_minor / 100:.2f}",
    )

    print(
        "Net incremental value / 1,000 failures:",
        f"₹{incremental_value_minor * 10:.2f}",
    )

    print(
        "Expected discount spend / failed order:",
        f"₹{discount_spend / 100:.2f}",
    )

    print(
        "Expected action cost / failed order:",
        f"₹{action_cost / 100:.2f}",
    )

    print(
        "Economic regret vs Oracle:",
        f"₹{regret_minor / 100:.2f}",
        "per failed order",
    )

    print()
    print(
        "Chosen actions:",
        dict(
            result[
                "actions"
            ]
        ),
    )

    summary_rows.append(
        {
            "policy":
                policy_name,

            "recovery_rate":
                recovery,

            "incremental_recovery_pp":
                incremental_recovery_pp,

            "intervention_rate":
                intervention_rate,

            "unnecessary_intervention_rate":
                unnecessary_rate,

            "merchant_value_minor_per_failure":
                merchant_value,

            "incremental_value_minor_per_failure":
                incremental_value_minor,

            "discount_spend_minor_per_failure":
                discount_spend,

            "action_cost_minor_per_failure":
                action_cost,

            "economic_regret_minor_per_failure":
                regret_minor,
        }
    )


DETAIL_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)


with DETAIL_PATH.open(
    "w",
    newline="",
    encoding="utf-8",
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=detail_rows[
            0
        ].keys(),
    )

    writer.writeheader()
    writer.writerows(
        detail_rows
    )


with SUMMARY_PATH.open(
    "w",
    newline="",
    encoding="utf-8",
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=summary_rows[
            0
        ].keys(),
    )

    writer.writeheader()
    writer.writerows(
        summary_rows
    )


print()
print(
    "Detailed evaluation saved:",
    DETAIL_PATH,
)

print(
    "Summary saved:",
    SUMMARY_PATH,
)
