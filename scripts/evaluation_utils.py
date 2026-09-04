"""Shared, behavior-preserving helpers for simulator evaluations."""

import copy
from collections import Counter

import numpy as np

from simulator.action_candidates import ActionCandidateGenerator
from simulator.customer_generator import CustomerGenerator
from simulator.decision_state import RecoveryDecisionStateBuilder
from simulator.historical_policy import HistoricalRecoveryPolicy
from simulator.history_generator import HistoricalJourneyGenerator
from simulator.intervention_engine import InterventionEngine
from simulator.journey_processor import JourneyProcessor
from simulator.method_selector import PaymentMethodSelector
from simulator.models import ActionType, PaymentStatus
from simulator.random_source import RandomSource


def branch_recovered(
    config,
    customer,
    journey,
    action,
    seed,
):
    """Run one independent simulator branch and report recovery."""

    branch_random = RandomSource(seed)
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
        attempt.status == PaymentStatus.CAPTURED
        for attempt in result.payment_attempts
    )


def estimate_true_probability(
    config,
    customer,
    journey,
    action,
    state_index,
    rollouts_per_action,
    seed_base,
):
    """Estimate simulator recovery probability with deterministic seeds."""

    successes = 0

    for rollout_index in range(rollouts_per_action):
        seed = (
            seed_base
            + state_index * 10_000
            + rollout_index
        )
        successes += int(
            branch_recovered(
                config=config,
                customer=customer,
                journey=journey,
                action=action,
                seed=seed,
            )
        )

    return successes / rollouts_per_action


def collect_evaluation_states(
    config,
    reference_time,
    target_states,
    world_seed,
    include_historical_probabilities=False,
):
    """Build fresh confirmed-failure states using factual history."""

    world_random = RandomSource(world_seed)
    customer_generator = CustomerGenerator(
        config=config,
        random_source=world_random,
    )
    history_generator = HistoricalJourneyGenerator(
        config=config,
        random_source=world_random,
        reference_time=reference_time,
    )
    processor = JourneyProcessor(
        config=config,
        random_source=world_random,
    )
    selector = PaymentMethodSelector(
        config=config,
        random_source=world_random,
    )
    state_builder = RecoveryDecisionStateBuilder(
        random_source=world_random,
        method_selector=selector,
    )
    candidate_generator = ActionCandidateGenerator(
        config=config,
        method_selector=selector,
    )
    historical_policy = HistoricalRecoveryPolicy(
        random_source=world_random,
    )
    intervention_engine = InterventionEngine(
        config=config,
        random_source=world_random,
        journey_processor=processor,
    )

    collected = []

    while len(collected) < target_states:
        customer = customer_generator.generate_customer()
        history = history_generator.generate_history(customer)
        observed_history = []

        for journey in history:
            processor.process_initial_attempt(
                customer=customer,
                journey=journey,
            )
            first_attempt = journey.payment_attempts[0]

            if first_attempt.status in {
                PaymentStatus.CAPTURED,
                PaymentStatus.UNCERTAIN,
            }:
                observed_history.append(journey)
                continue

            state = state_builder.build(
                customer=customer,
                current_journey=journey,
                prior_journeys=observed_history,
            )
            candidates = candidate_generator.generate_candidates(
                customer=customer,
                journey=journey,
            )
            eligible_with_probabilities = (
                historical_policy.action_probabilities(
                    state=state,
                    candidates=candidates,
                )
            )
            eligible_actions = [
                action
                for action, _ in eligible_with_probabilities
            ]

            state_record = (
                copy.deepcopy(customer),
                copy.deepcopy(journey),
                state,
                copy.deepcopy(eligible_actions),
            )
            if include_historical_probabilities:
                state_record += (
                    eligible_with_probabilities,
                )
            collected.append(state_record)

            observed_action, _ = historical_policy.choose_action(
                state=state,
                candidates=candidates,
            )
            observed_result = intervention_engine.simulate_action(
                customer=customer,
                journey=journey,
                action=observed_action,
            )
            observed_history.append(observed_result)

            if len(collected) >= target_states:
                break

    return collected


def evaluate_counterfactual_model(records, model_key):
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
        true_values = record["true"]
        predictions = record[model_key]
        shared_actions = [
            action
            for action in true_values
            if action in predictions
        ]

        if "NO_ACTION" not in shared_actions:
            continue

        evaluated_states += 1
        true_no_action = true_values["NO_ACTION"]
        predicted_no_action = predictions["NO_ACTION"]

        for action in shared_actions:
            true_probability = true_values[action]
            predicted_probability = predictions[action]
            probability_errors.append(
                abs(predicted_probability - true_probability)
            )

            if action != "NO_ACTION":
                true_uplift = true_probability - true_no_action
                predicted_uplift = (
                    predicted_probability
                    - predicted_no_action
                )
                uplift_errors.append(
                    abs(predicted_uplift - true_uplift)
                )
                true_uplifts.append(true_uplift)
                predicted_uplifts.append(predicted_uplift)

        true_best_action = max(
            shared_actions,
            key=lambda action: true_values[action],
        )
        predicted_best_action = max(
            shared_actions,
            key=lambda action: predictions[action],
        )
        chosen_actions[predicted_best_action] += 1

        if predicted_best_action == true_best_action:
            correct_best_action += 1

        policy_values.append(true_values[predicted_best_action])
        oracle_values.append(true_values[true_best_action])
        no_action_values.append(true_no_action)

    probability_mae = float(np.mean(probability_errors))
    uplift_mae = float(np.mean(uplift_errors))

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

    policy_value = float(np.mean(policy_values))
    oracle_value = float(np.mean(oracle_values))

    return {
        "probability_mae": probability_mae,
        "uplift_mae": uplift_mae,
        "uplift_correlation": uplift_correlation,
        "best_action_accuracy": (
            correct_best_action / evaluated_states
        ),
        "policy_value": policy_value,
        "oracle_value": oracle_value,
        "no_action_value": float(np.mean(no_action_values)),
        "regret": oracle_value - policy_value,
        "chosen_actions": chosen_actions,
    }


def print_counterfactual_results(name, results):
    """Print the shared counterfactual model metric format."""

    print()
    print(name)
    print("-" * len(name))
    print("Probability MAE:", f"{results['probability_mae']:.4f}")
    print("Uplift MAE:", f"{results['uplift_mae']:.4f}")
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
    print("Oracle value:", f"{results['oracle_value'] * 100:.2f}%")
    print("Regret vs Oracle:", f"{results['regret'] * 100:.2f} pp")
    print()
    print("Chosen actions:")

    for action, count in results["chosen_actions"].most_common():
        print(f"  {action:24}", count)


def find_action(actions, action_type):
    """Return the first action matching an action type."""

    for action in actions:
        if action.action_type == action_type:
            return action
    return None


def fixed_action_cost_minor(action, economics):
    """Return fixed intervention cost in minor currency units."""

    if action.action_type == ActionType.NUDGE:
        return economics.nudge_cost_minor
    if action.action_type == ActionType.SWITCH_METHOD:
        return economics.switch_cost_minor
    if action.action_type == ActionType.APPROVED_OFFER:
        return economics.offer_execution_cost_minor
    return 0.0


def expected_discount_spend_minor(
    state,
    action,
    recovery_probability,
):
    """Return expected discount spend for a successful offer."""

    if action.action_type != ActionType.APPROVED_OFFER:
        return 0.0

    discount = action.discount_percent or 0.0
    return (
        recovery_probability
        * state.current_amount_minor
        * discount
        / 100.0
    )
