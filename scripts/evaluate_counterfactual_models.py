import copy
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from simulator.action_candidates import ActionCandidateGenerator
from simulator.config import SimulatorConfig
from simulator.customer_generator import CustomerGenerator
from simulator.decision_state import RecoveryDecisionStateBuilder
from simulator.historical_policy import HistoricalRecoveryPolicy
from simulator.history_generator import HistoricalJourneyGenerator
from simulator.intervention_engine import InterventionEngine
from simulator.journey_processor import JourneyProcessor
from simulator.method_selector import PaymentMethodSelector
from simulator.models import (
    ActionType,
    PaymentStatus,
)
from simulator.random_source import RandomSource


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


def action_label(action):
    """Convert RecoveryAction into the treatment label used by ML."""

    if action.action_type == ActionType.SWITCH_METHOD:
        return (
            "SWITCH_"
            + action.target_method.value
        )

    if action.action_type == ActionType.APPROVED_OFFER:
        return (
            "OFFER_"
            + str(
                int(
                    action.discount_percent
                )
            )
        )

    return action.action_type.value


def state_to_row(state):
    """Convert observable decision state into one model-input row."""

    return {
        "customer_tenure_days":
            state.customer_tenure_days,

        "prior_checkout_count":
            state.prior_checkout_count,

        "prior_success_count":
            state.prior_success_count,

        "prior_failure_count":
            state.prior_failure_count,

        "prior_success_rate":
            state.prior_success_rate,

        "prior_upi_count":
            state.prior_upi_count,

        "prior_credit_card_count":
            state.prior_credit_card_count,

        "prior_debit_card_count":
            state.prior_debit_card_count,

        "prior_netbanking_count":
            state.prior_netbanking_count,

        "available_upi":
            int(state.available_upi),

        "available_credit_card":
            int(state.available_credit_card),

        "available_debit_card":
            int(state.available_debit_card),

        "available_netbanking":
            int(state.available_netbanking),

        "current_amount_minor":
            state.current_amount_minor,

        "amount_ratio":
            state.amount_ratio,

        "current_method":
            state.current_method.value,

        "failure_category":
            state.failure_category.value,

        "attempt_count":
            state.attempt_count,

        "observed_rail_health":
            state.observed_rail_health,

        "contact_consent":
            int(state.contact_consent),

        "customer_active":
            int(state.customer_active),
    }


def branch_recovered(
    customer,
    journey,
    action,
    seed,
):
    """
    Run one independent recovery branch.

    The same seed is reused across actions for the same rollout so the
    worlds share as much stochastic variation as practical.
    """

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
    """
    Monte Carlo estimate of simulator P(recovery | state, action).
    """

    successes = 0

    for rollout_index in range(
        ROLLOUTS_PER_ACTION
    ):
        seed = (
            5_000_000
            + state_index * 10_000
            + rollout_index
        )

        recovered = branch_recovered(
            customer=customer,
            journey=journey,
            action=action,
            seed=seed,
        )

        successes += int(
            recovered
        )

    return (
        successes
        / ROLLOUTS_PER_ACTION
    )


def collect_evaluation_states():
    """
    Generate fresh failed-payment states not used in the training dataset.
    """

    world_random = RandomSource(
        20260904
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

    method_selector = PaymentMethodSelector(
        config=config,
        random_source=world_random,
    )

    state_builder = (
        RecoveryDecisionStateBuilder(
            random_source=world_random,
            method_selector=method_selector,
        )
    )

    candidate_generator = (
        ActionCandidateGenerator(
            config=config,
            method_selector=method_selector,
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

    states = []

    while len(states) < EVALUATION_STATES:

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

            # Reuse the same eligibility logic as our historical policy.
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

            states.append(
                (
                    copy.deepcopy(customer),
                    copy.deepcopy(journey),
                    state,
                    eligible_actions,
                )
            )

            # Continue constructing realistic observed history for any
            # later Orders belonging to this customer.
            (
                observed_action,
                _,
            ) = historical_policy.choose_action(
                state=state,
                candidates=candidates,
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
                len(states)
                >= EVALUATION_STATES
            ):
                break

    return states


print()
print("BUILDING COUNTERFACTUAL TRUTH SET")
print("---------------------------------")

evaluation_states = (
    collect_evaluation_states()
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
            state_to_row(state)
        ]
    )

    true_probabilities = {}
    t_predictions = {}
    s_predictions = {}
    ipw_s_predictions = {}
    dr_predictions = {}

    for action in eligible_actions:

        label = action_label(
            action
        )

        true_probability = (
            estimate_true_probability(
                customer=customer,
                journey=journey,
                action=action,
                state_index=state_index,
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


def evaluate_model(
    records,
    model_key,
):
    """Measure probability and uplift quality against simulator truth."""

    probability_errors = []
    uplift_errors = []

    predicted_uplifts = []
    true_uplifts = []

    correct_best_action = 0

    policy_values = []
    oracle_values = []
    no_action_values = []

    chosen_actions = Counter()

    evaluated_states = 0

    for record in records:

        true_values = record[
            "true"
        ]

        predictions = record[
            model_key
        ]

        shared_actions = [
            action
            for action in true_values
            if action in predictions
        ]

        if (
            "NO_ACTION"
            not in shared_actions
        ):
            continue

        evaluated_states += 1

        true_no_action = (
            true_values[
                "NO_ACTION"
            ]
        )

        predicted_no_action = (
            predictions[
                "NO_ACTION"
            ]
        )

        for action in shared_actions:

            true_probability = (
                true_values[action]
            )

            predicted_probability = (
                predictions[action]
            )

            probability_errors.append(
                abs(
                    predicted_probability
                    - true_probability
                )
            )

            if action != "NO_ACTION":

                true_uplift = (
                    true_probability
                    - true_no_action
                )

                predicted_uplift = (
                    predicted_probability
                    - predicted_no_action
                )

                uplift_errors.append(
                    abs(
                        predicted_uplift
                        - true_uplift
                    )
                )

                true_uplifts.append(
                    true_uplift
                )

                predicted_uplifts.append(
                    predicted_uplift
                )

        true_best_action = max(
            shared_actions,
            key=lambda action:
                true_values[action],
        )

        predicted_best_action = max(
            shared_actions,
            key=lambda action:
                predictions[action],
        )

        chosen_actions[
            predicted_best_action
        ] += 1

        if (
            predicted_best_action
            == true_best_action
        ):
            correct_best_action += 1

        policy_values.append(
            true_values[
                predicted_best_action
            ]
        )

        oracle_values.append(
            true_values[
                true_best_action
            ]
        )

        no_action_values.append(
            true_no_action
        )

    probability_mae = float(
        np.mean(
            probability_errors
        )
    )

    uplift_mae = float(
        np.mean(
            uplift_errors
        )
    )

    if (
        np.std(true_uplifts) > 0
        and np.std(predicted_uplifts) > 0
    ):
        uplift_correlation = float(
            np.corrcoef(
                true_uplifts,
                predicted_uplifts,
            )[0, 1]
        )
    else:
        uplift_correlation = 0.0

    best_action_accuracy = (
        correct_best_action
        / evaluated_states
    )

    policy_value = float(
        np.mean(
            policy_values
        )
    )

    oracle_value = float(
        np.mean(
            oracle_values
        )
    )

    no_action_value = float(
        np.mean(
            no_action_values
        )
    )

    regret = (
        oracle_value
        - policy_value
    )

    return {
        "probability_mae":
            probability_mae,

        "uplift_mae":
            uplift_mae,

        "uplift_correlation":
            uplift_correlation,

        "best_action_accuracy":
            best_action_accuracy,

        "policy_value":
            policy_value,

        "oracle_value":
            oracle_value,

        "no_action_value":
            no_action_value,

        "regret":
            regret,

        "chosen_actions":
            chosen_actions,
    }


t_results = evaluate_model(
    truth_records,
    "t",
)

s_results = evaluate_model(
    truth_records,
    "s",
)

ipw_s_results = evaluate_model(
    truth_records,
    "ipw_s",
)

dr_results = evaluate_model(
    truth_records,
    "dr",
)

def print_results(
    name,
    results,
):

    print()
    print(name)
    print(
        "-" * len(name)
    )

    print(
        "Probability MAE:",
        f"{results['probability_mae']:.4f}",
    )

    print(
        "Uplift MAE:",
        f"{results['uplift_mae']:.4f}",
    )

    print(
        "Uplift correlation:",
        f"{results['uplift_correlation']:.4f}",
    )

    print(
        "Best-action accuracy:",
        f"{results['best_action_accuracy'] * 100:.2f}%",
    )

    print(
        "Policy recovery value:",
        f"{results['policy_value'] * 100:.2f}%",
    )

    print(
        "NO_ACTION value:",
        f"{results['no_action_value'] * 100:.2f}%",
    )

    print(
        "Oracle value:",
        f"{results['oracle_value'] * 100:.2f}%",
    )

    print(
        "Regret vs Oracle:",
        f"{results['regret'] * 100:.2f} pp",
    )

    print()
    print("Chosen actions:")

    for action, count in (
        results[
            "chosen_actions"
        ].most_common()
    ):
        print(
            f"  {action:24}",
            count,
        )


print()
print("COUNTERFACTUAL MODEL EVALUATION")
print("===============================")

print_results(
    "T-LEARNER",
    t_results,
)

print_results(
    "POOLED S-LEARNER",
    s_results,
)

print_results(
    "IPW POOLED S-LEARNER",
    ipw_s_results,
)

print_results(
    "DOUBLY ROBUST LEARNER",
    dr_results,
)