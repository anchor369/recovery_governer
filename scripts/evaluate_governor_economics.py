import copy
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
from simulator.action_candidates import (
    ActionCandidateGenerator,
)
from simulator.config import SimulatorConfig
from simulator.customer_generator import (
    CustomerGenerator,
)
from simulator.decision_state import (
    RecoveryDecisionStateBuilder,
)
from simulator.historical_policy import (
    HistoricalRecoveryPolicy,
)
from simulator.history_generator import (
    HistoricalJourneyGenerator,
)
from simulator.intervention_engine import (
    InterventionEngine,
)
from simulator.journey_processor import (
    JourneyProcessor,
)
from simulator.method_selector import (
    PaymentMethodSelector,
)
from simulator.models import (
    ActionType,
    PaymentStatus,
    RecoveryAction,
)
from simulator.random_source import RandomSource


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


def action_label(
    action: RecoveryAction,
) -> str:

    if (
        action.action_type
        == ActionType.SWITCH_METHOD
    ):
        return (
            "SWITCH_"
            + action.target_method.value
        )

    if (
        action.action_type
        == ActionType.APPROVED_OFFER
    ):
        return (
            "OFFER_"
            + str(
                int(
                    action.discount_percent
                )
            )
        )

    return action.action_type.value


def branch_recovered(
    customer,
    journey,
    action,
    seed,
):

    branch_random = RandomSource(
        seed
    )

    processor = JourneyProcessor(
        config=config,
        random_source=branch_random,
    )

    engine = InterventionEngine(
        config=config,
        random_source=branch_random,
        journey_processor=processor,
    )

    result = engine.simulate_action(
        customer=customer,
        journey=journey,
        action=action,
    )

    return any(
        attempt.status
        == PaymentStatus.CAPTURED
        for attempt
        in result.payment_attempts
    )


def estimate_true_probability(
    customer,
    journey,
    action,
    state_index,
):

    successes = 0

    for rollout_index in range(
        ROLLOUTS_PER_ACTION
    ):

        seed = (
            8_000_000
            + state_index * 10_000
            + rollout_index
        )

        successes += int(
            branch_recovered(
                customer=customer,
                journey=journey,
                action=action,
                seed=seed,
            )
        )

    return (
        successes
        / ROLLOUTS_PER_ACTION
    )


def collect_states():

    world_random = RandomSource(
        20260905
    )

    customer_generator = (
        CustomerGenerator(
            config=config,
            random_source=world_random,
        )
    )

    history_generator = (
        HistoricalJourneyGenerator(
            config=config,
            random_source=world_random,
            reference_time=REFERENCE_TIME,
        )
    )

    processor = JourneyProcessor(
        config=config,
        random_source=world_random,
    )

    selector = PaymentMethodSelector(
        config=config,
        random_source=world_random,
    )

    state_builder = (
        RecoveryDecisionStateBuilder(
            random_source=world_random,
            method_selector=selector,
        )
    )

    candidate_generator = (
        ActionCandidateGenerator(
            config=config,
            method_selector=selector,
        )
    )

    historical_policy = (
        HistoricalRecoveryPolicy(
            random_source=world_random,
        )
    )

    intervention_engine = (
        InterventionEngine(
            config=config,
            random_source=world_random,
            journey_processor=processor,
        )
    )

    collected = []

    while (
        len(collected)
        < EVALUATION_STATES
    ):

        customer = (
            customer_generator
            .generate_customer()
        )

        history = (
            history_generator
            .generate_history(customer)
        )

        observed_history = []

        for journey in history:

            processor.process_initial_attempt(
                customer=customer,
                journey=journey,
            )

            first_attempt = (
                journey.payment_attempts[0]
            )

            if (
                first_attempt.status
                == PaymentStatus.CAPTURED
            ):
                observed_history.append(
                    journey
                )
                continue

            if (
                first_attempt.status
                == PaymentStatus.UNCERTAIN
            ):
                observed_history.append(
                    journey
                )
                continue

            state = state_builder.build(
                customer=customer,
                current_journey=journey,
                prior_journeys=observed_history,
            )

            candidates = (
                candidate_generator
                .generate_candidates(
                    customer=customer,
                    journey=journey,
                )
            )

            eligible_with_probabilities = (
                historical_policy
                .action_probabilities(
                    state=state,
                    candidates=candidates,
                )
            )

            eligible_actions = [
                action
                for action, _
                in eligible_with_probabilities
            ]

            collected.append(
                (
                    copy.deepcopy(customer),
                    copy.deepcopy(journey),
                    state,
                    copy.deepcopy(
                        eligible_actions
                    ),
                    eligible_with_probabilities,
                )
            )

            # Continue factual synthetic history.
            observed_action, _ = (
                historical_policy.choose_action(
                    state=state,
                    candidates=candidates,
                )
            )

            observed_result = (
                intervention_engine
                .simulate_action(
                    customer=customer,
                    journey=journey,
                    action=observed_action,
                )
            )

            observed_history.append(
                observed_result
            )

            if (
                len(collected)
                >= EVALUATION_STATES
            ):
                break

    return collected


def find_action(
    actions,
    action_type,
):

    for action in actions:

        if (
            action.action_type
            == action_type
        ):
            return action

    return None


def fixed_action_cost_minor(
    action,
):

    if (
        action.action_type
        == ActionType.NUDGE
    ):
        return (
            economics.nudge_cost_minor
        )

    if (
        action.action_type
        == ActionType.SWITCH_METHOD
    ):
        return (
            economics.switch_cost_minor
        )

    if (
        action.action_type
        == ActionType.APPROVED_OFFER
    ):
        return (
            economics.offer_execution_cost_minor
        )

    return 0.0


def expected_discount_spend_minor(
    state,
    action,
    recovery_probability,
):

    if (
        action.action_type
        != ActionType.APPROVED_OFFER
    ):
        return 0.0

    discount = (
        action.discount_percent
        or 0.0
    )

    return (
        recovery_probability
        * state.current_amount_minor
        * discount
        / 100.0
    )


print()
print("BUILDING ECONOMIC EVALUATION SET")
print("--------------------------------")

evaluation_states = collect_states()

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

        label = action_label(
            action
        )

        true_probabilities[
            label
        ] = (
            estimate_true_probability(
                customer=customer,
                journey=journey,
                action=action,
                state_index=state_index,
            )
        )

    no_action = find_action(
        eligible_actions,
        ActionType.NO_ACTION,
    )

    no_action_label = action_label(
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

        label = action_label(
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
                action_label(action)
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

        label = action_label(
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
                action_label(action)
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

        label = action_label(
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
                action
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