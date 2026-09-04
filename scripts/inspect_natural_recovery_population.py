from collections import Counter, defaultdict
from datetime import datetime, timezone

from simulator.config import SimulatorConfig
from simulator.customer_generator import CustomerGenerator
from simulator.history_generator import HistoricalJourneyGenerator
from simulator.journey_processor import JourneyProcessor
from simulator.models import PaymentStatus
from simulator.random_source import RandomSource


REFERENCE_TIME = datetime(
    2026,
    9,
    4,
    tzinfo=timezone.utc,
)

CUSTOMER_COUNT = 5000


config = SimulatorConfig()

random_source = RandomSource(
    config.random_seed
)

customer_generator = CustomerGenerator(
    config=config,
    random_source=random_source,
)

history_generator = HistoricalJourneyGenerator(
    config=config,
    random_source=random_source,
    reference_time=REFERENCE_TIME,
)

processor = JourneyProcessor(
    config=config,
    random_source=random_source,
)


first_attempt_statuses = Counter()

final_outcomes = Counter()

initial_failure_counts = Counter()
recovery_by_failure = defaultdict(Counter)

attempt_count_distribution = Counter()

natural_switch_count = 0

failed_first_attempt_count = 0


for _ in range(CUSTOMER_COUNT):

    customer = (
        customer_generator.generate_customer()
    )

    history = history_generator.generate_history(
        customer
    )

    for journey in history:

        processor.process_initial_attempt(
            customer=customer,
            journey=journey,
        )

        first_attempt = journey.payment_attempts[0]

        first_attempt_statuses[
            first_attempt.status
        ] += 1

        # Journeys paid immediately do not need recovery.
        if first_attempt.status == PaymentStatus.CAPTURED:

            final_outcomes[
                "PAID_FIRST_ATTEMPT"
            ] += 1

            attempt_count_distribution[1] += 1
            continue

        # Uncertain payments must not enter recovery.
        if first_attempt.status == PaymentStatus.UNCERTAIN:

            final_outcomes[
                "UNCERTAIN"
            ] += 1

            attempt_count_distribution[1] += 1
            continue

        failed_first_attempt_count += 1

        initial_failure = (
            first_attempt.failure_category
        )

        initial_failure_counts[
            initial_failure
        ] += 1

        processor.process_natural_recovery(
            customer=customer,
            journey=journey,
        )

        final_attempt = journey.payment_attempts[-1]

        attempt_count_distribution[
            len(journey.payment_attempts)
        ] += 1

        # Detect whether the customer naturally changed payment method.
        methods_used = {
            attempt.method
            for attempt in journey.payment_attempts
        }

        if len(methods_used) > 1:
            natural_switch_count += 1

        if journey.naturally_recovered:

            final_outcomes[
                "NATURALLY_RECOVERED"
            ] += 1

            recovery_by_failure[
                initial_failure
            ][
                "RECOVERED"
            ] += 1

        elif final_attempt.status == PaymentStatus.UNCERTAIN:

            final_outcomes[
                "ENDED_UNCERTAIN"
            ] += 1

            recovery_by_failure[
                initial_failure
            ][
                "UNCERTAIN"
            ] += 1

        else:

            final_outcomes[
                "ABANDONED_OR_UNRECOVERED"
            ] += 1

            recovery_by_failure[
                initial_failure
            ][
                "NOT_RECOVERED"
            ] += 1


def percentage(
    count: int,
    total: int,
) -> float:

    if total == 0:
        return 0.0

    return (
        count / total
    ) * 100


total_journeys = sum(
    first_attempt_statuses.values()
)


print()
print("NATURAL RECOVERY POPULATION")
print("---------------------------")

print(
    "Customers:",
    CUSTOMER_COUNT,
)

print(
    "Historical journeys:",
    total_journeys,
)


print()
print("FIRST ATTEMPT")
print("-------------")

for status in (
    PaymentStatus.CAPTURED,
    PaymentStatus.FAILED,
    PaymentStatus.UNCERTAIN,
):

    count = first_attempt_statuses[
        status
    ]

    print(
        f"{status.value:12}",
        count,
        f"({percentage(count, total_journeys):.2f}%)",
    )


print()
print("AFTER NO_ACTION")
print("---------------")

for outcome, count in final_outcomes.items():

    print(
        f"{outcome:26}",
        count,
        f"({percentage(count, total_journeys):.2f}% of all journeys)",
    )


natural_recovered = final_outcomes[
    "NATURALLY_RECOVERED"
]


print()
print("RECOVERY AMONG FIRST-ATTEMPT FAILURES")
print("-------------------------------------")

print(
    "First-attempt failures:",
    failed_first_attempt_count,
)

print(
    "Naturally recovered:",
    natural_recovered,
    f"({percentage(natural_recovered, failed_first_attempt_count):.2f}%)",
)


print()
print("RECOVERY BY INITIAL FAILURE")
print("---------------------------")

for failure_category, counts in (
    initial_failure_counts.most_common()
):

    recovered = recovery_by_failure[
        failure_category
    ][
        "RECOVERED"
    ]

    uncertain = recovery_by_failure[
        failure_category
    ][
        "UNCERTAIN"
    ]

    total = initial_failure_counts[
        failure_category
    ]

    print()
    print(
        failure_category.value
    )

    print(
        "  Cases:",
        total,
    )

    print(
        "  Recovered:",
        f"{percentage(recovered, total):.2f}%",
    )

    print(
        "  Ended uncertain:",
        f"{percentage(uncertain, total):.2f}%",
    )


print()
print("PAYMENT ATTEMPT COUNTS")
print("----------------------")

for attempt_count in sorted(
    attempt_count_distribution
):

    count = attempt_count_distribution[
        attempt_count
    ]

    print(
        f"{attempt_count} attempt(s):",
        count,
        f"({percentage(count, total_journeys):.2f}%)",
    )


print()
print("NATURAL METHOD SWITCHING")
print("------------------------")

print(
    "Failed journeys that used >1 method:",
    natural_switch_count,
    f"({percentage(natural_switch_count, failed_first_attempt_count):.2f}%)",
)