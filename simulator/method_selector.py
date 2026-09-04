"""
Payment-method availability and initial method-selection logic.

The selector uses only instruments possessed by the synthetic customer.
Order value can shift method preference without creating hard thresholds.
"""

import math

from simulator.config import SimulatorConfig
from simulator.models import (
    PaymentMethod,
    SyntheticCustomer,
)
from simulator.random_source import RandomSource


class PaymentMethodSelector:
    """
    Selects an available payment method for a synthetic customer.
    """

    def __init__(
        self,
        config: SimulatorConfig,
        random_source: RandomSource,
    ):
        self.config = config
        self.random = random_source

    def get_available_methods(
        self,
        customer: SyntheticCustomer,
    ) -> list[PaymentMethod]:
        """Return payment methods currently possessed by the customer."""

        methods = [PaymentMethod.UPI]

        if customer.credit_cards:
            methods.append(
                PaymentMethod.CREDIT_CARD
            )

        if any(
            account.debit_card_available
            for account in customer.bank_accounts
        ):
            methods.append(
                PaymentMethod.DEBIT_CARD
            )

        if any(
            account.netbanking_enabled
            for account in customer.bank_accounts
        ):
            methods.append(
                PaymentMethod.NETBANKING
            )

        return methods

    def choose_initial_method(
        self,
        customer: SyntheticCustomer,
        amount_minor: int,
    ) -> PaymentMethod:
        """
        Select the payment method used for the first attempt.

        Habitual behaviour provides a preference, while unusually large
        Orders gradually make Credit Card and Netbanking more plausible.
        """

        available_methods = self.get_available_methods(
            customer
        )

        weights = {
            PaymentMethod.UPI:
                self.config.habitual_upi_weight,

            PaymentMethod.CREDIT_CARD:
                self.config.habitual_credit_card_weight,

            PaymentMethod.DEBIT_CARD:
                self.config.habitual_debit_card_weight,

            PaymentMethod.NETBANKING:
                self.config.habitual_netbanking_weight,
        }

        # Flexible customers are less strongly tied to their habitual method.
        habitual_multiplier = (
            1.0
            + self.config.habitual_method_bias
            * (1.0 - customer.method_flexibility)
        )

        weights[
            customer.habitual_method
        ] *= habitual_multiplier

        amount_ratio = (
            amount_minor
            / customer.typical_order_value_minor
        )

        high_amount_pressure = max(
            0.0,
            math.log(amount_ratio),
        )

        weights[PaymentMethod.UPI] *= math.exp(
            -self.config.upi_high_amount_penalty
            * high_amount_pressure
        )

        weights[
            PaymentMethod.CREDIT_CARD
        ] *= math.exp(
            self.config.credit_card_high_amount_boost
            * high_amount_pressure
        )

        weights[
            PaymentMethod.NETBANKING
        ] *= math.exp(
            self.config.netbanking_high_amount_boost
            * high_amount_pressure
        )

        available_weights = [
            weights[method]
            for method in available_methods
        ]

        total_weight = sum(
            available_weights
        )

        probabilities = [
            weight / total_weight
            for weight in available_weights
        ]

        return self.random.choice(
            available_methods,
            probabilities=probabilities,
        )