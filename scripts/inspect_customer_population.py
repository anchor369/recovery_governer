import numpy as np

from simulator.config import SimulatorConfig
from simulator.customer_generator import CustomerGenerator
from simulator.models import PaymentMethod
from simulator.random_source import RandomSource


config = SimulatorConfig()

generator = CustomerGenerator(
    config=config,
    random_source=RandomSource(config.random_seed),
)

customers = [
    generator.generate_customer()
    for _ in range(10000)
]


def values(attribute_name):
    return np.array([
        getattr(customer, attribute_name)
        for customer in customers
    ])


print("\nCUSTOMER POPULATION SUMMARY")
print("---------------------------")

print(
    "Merchant affinity mean:",
    round(values("merchant_affinity").mean(), 3),
)

print(
    "Retry persistence mean:",
    round(values("retry_persistence").mean(), 3),
)

print(
    "Method flexibility mean:",
    round(values("method_flexibility").mean(), 3),
)

print(
    "Price sensitivity mean:",
    round(values("price_sensitivity").mean(), 3),
)

print(
    "Checkout rate mean:",
    round(values("checkout_rate_per_year").mean(), 2),
)

order_values_rupees = (
    values("typical_order_value_minor") / 100
)

print(
    "Typical order median:",
    round(np.median(order_values_rupees), 2),
)

print(
    "Typical order 90th percentile:",
    round(np.percentile(order_values_rupees, 90), 2),
)

print("\nHABITUAL PAYMENT METHODS")
print("------------------------")

for method in PaymentMethod:
    count = sum(
        customer.habitual_method == method
        for customer in customers
    )

    percentage = (
        count / len(customers)
    ) * 100

    print(
        method.value,
        round(percentage, 2),
        "%",
    )