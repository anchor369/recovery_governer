"""
Generates synthetic customers and their payment instruments.

The generator creates hidden behavioural state and factual synthetic
payment instruments. Hidden simulator state must not be passed directly
to the ML feature pipeline.
"""

import math

from simulator.config import SimulatorConfig
from simulator.models import (
    BankAccount,
    CreditCard,
    PaymentMethod,
    SyntheticCustomer,
)
from simulator.random_source import RandomSource


class CustomerGenerator:
    """
    Creates synthetic customers using one simulator configuration.

    Customer IDs are sequential so generated populations are easy to
    inspect and reproduce while debugging.
    """

    def __init__(
        self,
        config: SimulatorConfig,
        random_source: RandomSource,
    ):
        self.config = config
        self.random = random_source
        self.customer_counter = 0

    def generate_customer(self) -> SyntheticCustomer:
        """
        Generate one synthetic customer.

        Returns a customer containing behavioural simulator state,
        purchasing parameters and available payment instruments.
        """

        self.customer_counter += 1
        customer_id = f"C{self.customer_counter:06d}"

        merchant_affinity = self.random.beta(
            self.config.merchant_affinity_alpha,
            self.config.merchant_affinity_beta,
        )

        retry_persistence = self.random.beta(
            self.config.retry_persistence_alpha,
            self.config.retry_persistence_beta,
        )

        method_flexibility = self.random.beta(
            self.config.method_flexibility_alpha,
            self.config.method_flexibility_beta,
        )

        price_sensitivity = self.random.beta(
            self.config.price_sensitivity_alpha,
            self.config.price_sensitivity_beta,
        )

        checkout_rate_per_year = self.random.gamma(
            self.config.checkout_rate_shape,
            self.config.checkout_rate_scale,
        )

        customer_tenure_days = round(
            self._sample_truncated_lognormal(
                median=self.config.customer_tenure_median_days,
                sigma=self.config.customer_tenure_sigma,
                minimum=self.config.min_customer_tenure_days,
                maximum=self.config.max_customer_tenure_days,
            )
        )

        contact_consent=self.random.bernoulli(
        self.config.contact_consent_probability
        )

        typical_order_rupees = self._sample_truncated_lognormal(
            median=self.config.typical_order_median_rupees,
            sigma=self.config.typical_order_sigma,
            minimum=self.config.min_typical_order_rupees,
            maximum=self.config.max_typical_order_rupees,
        )

        typical_order_value_minor = round(typical_order_rupees * 100)

        bank_accounts = self._generate_bank_accounts(customer_id)
        credit_cards = self._generate_credit_cards(customer_id)

        habitual_method = self._choose_habitual_method(
            bank_accounts,
            credit_cards,
        )

        return SyntheticCustomer(
            customer_id=customer_id,
            created_at_days_ago=customer_tenure_days,
            merchant_affinity=merchant_affinity,
            retry_persistence=retry_persistence,
            method_flexibility=method_flexibility,
            price_sensitivity=price_sensitivity,
            checkout_rate_per_year=checkout_rate_per_year,
            typical_order_value_minor=typical_order_value_minor,
            habitual_method=habitual_method,
            bank_accounts=bank_accounts,
            credit_cards=credit_cards,
            contact_consent=contact_consent,
        )

    def _sample_truncated_lognormal(
        self,
        median: float,
        sigma: float,
        minimum: float,
        maximum: float,
    ) -> float:
        """
        Sample a log-normal value restricted to an allowed range.

        Values outside the range are sampled again instead of being
        clipped to avoid artificial piles at the minimum or maximum.
        """

        log_mean = math.log(median)

        for _ in range(100):
            sampled_value = self.random.lognormal(
                mean=log_mean,
                sigma=sigma,
            )

            if minimum <= sampled_value <= maximum:
                return sampled_value

        raise RuntimeError(
            "Could not sample a valid truncated log-normal value."
        )

    def _generate_bank_accounts(
        self,
        customer_id: str,
    ) -> list[BankAccount]:
        """Generate one or two synthetic bank accounts."""

        account_count = 1

        if self.random.bernoulli(
            self.config.second_bank_account_probability
        ):
            account_count = 2

        accounts = []

        for account_number in range(1, account_count + 1):
            account = BankAccount(
                account_id=f"{customer_id}_BA{account_number}",
                bank_id=f"BANK_{self.random.integer(1, 9):02d}",
                upi_enabled=True,
                debit_card_available=self.random.bernoulli(
                    self.config.debit_card_probability_per_account
                ),
                netbanking_enabled=self.random.bernoulli(
                    self.config.netbanking_probability_per_account
                ),
            )

            accounts.append(account)

        return accounts

    def _generate_credit_cards(
        self,
        customer_id: str,
    ) -> list[CreditCard]:
        """Generate a Credit Card for customers who have one."""

        if not self.random.bernoulli(
            self.config.credit_card_probability
        ):
            return []

        networks = ["VISA", "MASTERCARD", "RUPAY"]

        network = str(self.random.choice(networks))

        card = CreditCard(
            card_id=f"{customer_id}_CC1",
            issuer_bank_id=f"BANK_{self.random.integer(1, 9):02d}",
            network=network,
        )

        return [card]

    def _choose_habitual_method(
        self,
        bank_accounts: list[BankAccount],
        credit_cards: list[CreditCard],
    ) -> PaymentMethod:
        """
        Choose the customer's usual first-choice payment method.

        Only payment methods actually available to the synthetic customer
        participate in the choice.
        """

        method_weights = {
            PaymentMethod.UPI:
                self.config.habitual_upi_weight,

            PaymentMethod.CREDIT_CARD:
                self.config.habitual_credit_card_weight,

            PaymentMethod.DEBIT_CARD:
                self.config.habitual_debit_card_weight,

            PaymentMethod.NETBANKING:
                self.config.habitual_netbanking_weight,
        }

        available_methods = [PaymentMethod.UPI]

        if credit_cards:
            available_methods.append(PaymentMethod.CREDIT_CARD)

        if any(
            account.debit_card_available
            for account in bank_accounts
        ):
            available_methods.append(PaymentMethod.DEBIT_CARD)

        if any(
            account.netbanking_enabled
            for account in bank_accounts
        ):
            available_methods.append(PaymentMethod.NETBANKING)

        available_weights = [
            method_weights[method]
            for method in available_methods
        ]

        total_weight = sum(available_weights)

        normalized_weights = [
            weight / total_weight
            for weight in available_weights
        ]

        chosen_method = self.random.choice(
            available_methods,
            probabilities=normalized_weights,
        )

        return chosen_method