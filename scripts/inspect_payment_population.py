from collections import Counter, defaultdict
from datetime import datetime, timezone

from simulator.config import SimulatorConfig
from simulator.customer_generator import CustomerGenerator
from simulator.history_generator import (
    HistoricalJourneyGenerator,
)
from simulator.journey_processor import JourneyProcessor
from simulator.models import (
    IncidentMode,
    PaymentMethod,
    PaymentStatus,
)
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

journey_processor = JourneyProcessor(
    config=config,
    random_source=random_source,
)


status_counts = Counter()
method_counts = Counter()
method_status_counts = defaultdict(Counter)
failure_counts = Counter()

upi_healthy_statuses = Counter()

environment_mode_counts = Counter()

total_attempts = 0


for _ in range(CUSTOMER_COUNT):

    customer = (
        customer_generator.generate_customer()
    )

    history = history_generator.generate_history(
        customer
    )

    for journey in history:

        environment = (
            journey_processor.process_initial_attempt(
                customer=customer,
                journey=journey,
            )
        )

        attempt = journey.payment_attempts[0]

        total_attempts += 1

        status_counts[
            attempt.status
        ] += 1

        method_counts[
            attempt.method
        ] += 1

        method_status_counts[
            attempt.method
        ][
            attempt.status
        ] += 1

        environment_mode_counts[
            environment.incident_mode
        ] += 1

        if attempt.failure_category is not None:
            failure_counts[
                attempt.failure_category
            ] += 1

        if (
            attempt.method == PaymentMethod.UPI
            and environment.incident_mode
            == IncidentMode.NONE
        ):
            upi_healthy_statuses[
                attempt.status
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


print()
print("PAYMENT POPULATION SUMMARY")
print("--------------------------")

print(
    "Customers:",
    CUSTOMER_COUNT,
)

print(
    "Historical payment attempts:",
    total_attempts,
)

print()


print("OVERALL PAYMENT STATUS")
print("----------------------")

for status in PaymentStatus:

    if status == PaymentStatus.CREATED:
        continue

    count = status_counts[status]

    print(
        f"{status.value:12}",
        count,
        f"({percentage(count, total_attempts):.2f}%)",
    )


print()
print("PAYMENT METHOD RESULTS")
print("----------------------")

for method in PaymentMethod:

    method_total = method_counts[method]

    if method_total == 0:
        continue

    captured = (
        method_status_counts[
            method
        ][
            PaymentStatus.CAPTURED
        ]
    )

    failed = (
        method_status_counts[
            method
        ][
            PaymentStatus.FAILED
        ]
    )

    uncertain = (
        method_status_counts[
            method
        ][
            PaymentStatus.UNCERTAIN
        ]
    )

    print()
    print(method.value)

    print(
        "  Attempts:",
        method_total,
    )

    print(
        "  Captured:",
        f"{percentage(captured, method_total):.2f}%",
    )

    print(
        "  Failed:",
        f"{percentage(failed, method_total):.2f}%",
    )

    print(
        "  Uncertain:",
        f"{percentage(uncertain, method_total):.2f}%",
    )


print()
print("FAILURE CATEGORIES")
print("------------------")

failed_total = status_counts[
    PaymentStatus.FAILED
]

for category, count in (
    failure_counts.most_common()
):

    print(
        f"{category.value:32}",
        count,
        f"({percentage(count, failed_total):.2f}% of failures)",
    )


print()
print("INFRASTRUCTURE MODES")
print("--------------------")

for mode in IncidentMode:

    count = environment_mode_counts[
        mode
    ]

    print(
        f"{mode.value:24}",
        f"{percentage(count, total_attempts):.2f}%",
    )


print()
print("HEALTHY UPI ONLY")
print("----------------")

healthy_upi_total = sum(
    upi_healthy_statuses.values()
)

for status in (
    PaymentStatus.CAPTURED,
    PaymentStatus.FAILED,
    PaymentStatus.UNCERTAIN,
):

    count = upi_healthy_statuses[
        status
    ]

    print(
        f"{status.value:12}",
        f"{percentage(count, healthy_upi_total):.2f}%",
    )