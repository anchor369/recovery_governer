from datetime import datetime, timezone

from simulator.config import SimulatorConfig
from simulator.customer_generator import CustomerGenerator
from simulator.history_generator import (
    HistoricalJourneyGenerator,
)
from simulator.random_source import RandomSource


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
    reference_time=datetime(
        2026,
        9,
        4,
        tzinfo=timezone.utc,
    ),
)

customer = customer_generator.generate_customer()

history = history_generator.generate_history(
    customer
)

print("\nCUSTOMER")
print("--------")
print("ID:", customer.customer_id)
print(
    "Tenure:",
    customer.created_at_days_ago,
    "days",
)
print(
    "Checkout rate:",
    round(
        customer.checkout_rate_per_year,
        2,
    ),
    "/year",
)
print(
    "Typical Order: INR",
    customer.typical_order_value_minor / 100,
)

print("\nHISTORY")
print("-------")

for journey in history:
    print(
        journey.created_at.date(),
        "INR",
        round(
            journey.amount_minor / 100,
            2,
        ),
    )

print(
    "\nHistorical checkouts:",
    len(history),
)
