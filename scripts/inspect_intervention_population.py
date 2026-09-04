from collections import defaultdict
from datetime import datetime, timezone

from simulator.action_candidates import ActionCandidateGenerator
from simulator.config import SimulatorConfig
from simulator.customer_generator import CustomerGenerator
from simulator.history_generator import HistoricalJourneyGenerator
from simulator.intervention_engine import InterventionEngine
from simulator.journey_processor import JourneyProcessor
from simulator.method_selector import PaymentMethodSelector
from simulator.models import (
    ActionType,
    PaymentStatus,
    RecoveryAction,
)
from simulator.random_source import RandomSource
from simulator.action_codec import (
    action_to_label,
)

REFERENCE_TIME = datetime(
    2026,
    9,
    4,
    tzinfo=timezone.utc,
)

FAILED_STATE_TARGET = 600
ROLLOUTS_PER_STATE = 15


config = SimulatorConfig()

world_random = RandomSource(
    config.random_seed
)

customer_generator = CustomerGenerator(
    config,
    world_random,
)

history_generator = HistoricalJourneyGenerator(
    config,
    world_random,
    REFERENCE_TIME,
)

initial_processor = JourneyProcessor(
    config,
    world_random,
)

candidate_generator = ActionCandidateGenerator(
    config=config,
    method_selector=PaymentMethodSelector(
        config,
        RandomSource(999),
    ),
)


failed_states = []


while len(failed_states) < FAILED_STATE_TARGET:

    customer = (
        customer_generator.generate_customer()
    )

    history = history_generator.generate_history(
        customer
    )

    for journey in history:

        initial_processor.process_initial_attempt(
            customer,
            journey,
        )

        if (
            journey.payment_attempts[-1].status
            == PaymentStatus.FAILED
        ):
            failed_states.append(
                (customer, journey)
            )

            if (
                len(failed_states)
                >= FAILED_STATE_TARGET
            ):
                break


def branch_paid(
    customer,
    journey,
    action,
    seed,
):
    """
    Run one independent counterfactual branch.

    Every action for the same state/rollout receives the same seed so
    comparisons have partially matched randomness.
    """

    branch_random = RandomSource(seed)

    branch_processor = JourneyProcessor(
        config,
        branch_random,
    )

    branch_engine = InterventionEngine(
        config=config,
        random_source=branch_random,
        journey_processor=branch_processor,
    )

    result = branch_engine.simulate_action(
        customer=customer,
        journey=journey,
        action=action,
    )

    return any(
        attempt.status == PaymentStatus.CAPTURED
        for attempt in result.payment_attempts
    )

def action_display_label(action):
    """
    Format canonical action labels for human-readable
    simulator inspection output.
    """

    label = action_to_label(
        action
    )

    if label.startswith(
        "SWITCH_"
    ):
        return label.replace(
            "SWITCH_",
            "SWITCH->",
            1,
        )

    if label.startswith(
        "OFFER_"
    ):
        return (
            label
            + "%"
        )

    return label

stats = defaultdict(
    lambda: {
        "trials": 0,
        "successes": 0,
        "paired_no_action_successes": 0,
    }
)

overall_no_action_trials = 0
overall_no_action_successes = 0


for state_index, (
    customer,
    journey,
) in enumerate(failed_states):

    candidates = (
        candidate_generator.generate_candidates(
            customer,
            journey,
        )
    )

    non_baseline_candidates = [
        action
        for action in candidates
        if action.action_type
        != ActionType.NO_ACTION
    ]

    for rollout_index in range(
        ROLLOUTS_PER_STATE
    ):

        branch_seed = (
            100_000
            + state_index * 100
            + rollout_index
        )

        no_action = RecoveryAction(
            action_type=ActionType.NO_ACTION,
        )

        baseline_paid = branch_paid(
            customer=customer,
            journey=journey,
            action=no_action,
            seed=branch_seed,
        )

        overall_no_action_trials += 1
        overall_no_action_successes += int(
            baseline_paid
        )

        for action in non_baseline_candidates:

            paid = branch_paid(
                customer=customer,
                journey=journey,
                action=action,
                seed=branch_seed,
            )

            label = action_display_label(action)

            stats[label]["trials"] += 1
            stats[label]["successes"] += int(
                paid
            )

            # Paired baseline for exactly the states where this action
            # was structurally available.
            stats[label][
                "paired_no_action_successes"
            ] += int(baseline_paid)


def percent(
    numerator,
    denominator,
):
    if denominator == 0:
        return 0.0

    return (
        numerator
        / denominator
        * 100.0
    )


print()
print("COUNTERFACTUAL ACTION BENCHMARK")
print("-------------------------------")

print(
    "Failed starting states:",
    len(failed_states),
)

print(
    "Rollouts per state:",
    ROLLOUTS_PER_STATE,
)


baseline_rate = percent(
    overall_no_action_successes,
    overall_no_action_trials,
)


print()
print("GLOBAL NO_ACTION")
print("----------------")

print(
    "Recovery rate:",
    f"{baseline_rate:.2f}%",
)


print()
print("ACTION RESULTS")
print("--------------")

for label in sorted(stats):

    result = stats[label]

    trials = result["trials"]

    action_rate = percent(
        result["successes"],
        trials,
    )

    paired_baseline_rate = percent(
        result[
            "paired_no_action_successes"
        ],
        trials,
    )

    uplift = (
        action_rate
        - paired_baseline_rate
    )

    print()
    print(label)

    print(
        "  Trials:",
        trials,
    )

    print(
        "  Action recovery:",
        f"{action_rate:.2f}%",
    )

    print(
        "  Paired NO_ACTION:",
        f"{paired_baseline_rate:.2f}%",
    )

    print(
        "  Absolute uplift:",
        f"{uplift:+.2f} percentage points",
    )