from simulator.config import SimulatorConfig
from simulator.customer_generator import CustomerGenerator
from simulator.order_behavior import OrderBehaviorModel
from simulator.random_source import RandomSource


def test_order_propensity_stays_between_zero_and_one():
    config = SimulatorConfig()
    random_source = RandomSource(42)

    customer_generator = CustomerGenerator(
        config,
        random_source,
    )

    behavior = OrderBehaviorModel(
        config,
        random_source,
    )

    for _ in range(5000):
        customer = (
            customer_generator.generate_customer()
        )

        motivation = (
            behavior.sample_base_motivation()
        )

        propensity = behavior.calculate_propensity(
            customer=customer,
            amount_minor=(
                customer.typical_order_value_minor
            ),
            base_motivation=motivation,
        )

        assert 0.0 <= propensity <= 1.0


