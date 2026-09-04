"""
Natural customer behaviour after a confirmed payment failure.

This module represents what can happen when the recovery system takes
NO_ACTION. Customers may retry, switch methods, return later or abandon.
"""

import math
from datetime import timedelta

from simulator.config import SimulatorConfig
from simulator.method_selector import PaymentMethodSelector
from simulator.models import (
    FailureCategory,
    HistoricalJourney,
    NaturalAction,
    PaymentAttempt,
    PaymentMethod,
    PaymentStatus,
    SyntheticCustomer,
)
from simulator.random_source import RandomSource


class NaturalRecoveryEngine:
    """Generates customer behaviour after confirmed payment failures."""

    def __init__(
        self,
        config: SimulatorConfig,
        random_source: RandomSource,
    ):
        self.config = config
        self.random = random_source

        self.method_selector = PaymentMethodSelector(
            config=config,
            random_source=random_source,
        )

    def choose_next_action(
        self,
        customer: SyntheticCustomer,
        journey: HistoricalJourney,
    ) -> NaturalAction:
        """
        Choose what the customer naturally does after the latest failure.
        """

        last_attempt = journey.payment_attempts[-1]

        if last_attempt.status != PaymentStatus.FAILED:
            raise ValueError(
                "Natural recovery can only follow a confirmed failure."
            )

        continue_probability = (
            self._continuation_probability(
                customer=customer,
                journey=journey,
            )
        )

        if not self.random.bernoulli(
            continue_probability
        ):
            # Some customers leave but may still return later.
            return_probability = (
                0.15
                + 0.35
                * journey.latent_order_propensity
                + 0.15
                * customer.merchant_affinity
            )

            return_probability = min(
                return_probability,
                0.75,
            )

            if self.random.bernoulli(
                return_probability
            ):
                return NaturalAction.RETURN_LATER

            return NaturalAction.ABANDON

        return self._choose_active_action(
            customer=customer,
            journey=journey,
        )

    def create_next_attempt(
        self,
        customer: SyntheticCustomer,
        journey: HistoricalJourney,
        action: NaturalAction,
    ) -> PaymentAttempt | None:
        """
        Create the next payment attempt when an action leads to one.

        ABANDON creates no new payment attempt.
        """

        if action == NaturalAction.ABANDON:
            journey.abandoned = True
            return None

        previous_attempt = journey.payment_attempts[-1]

        next_attempt_number = (
            previous_attempt.attempt_number + 1
        )

        if (
            next_attempt_number
            > self.config.max_payment_attempts
        ):
            journey.abandoned = True
            return None

        if action == NaturalAction.SWITCH_METHOD:
            next_method = self._choose_alternate_method(
                customer=customer,
                current_method=previous_attempt.method,
            )

            if next_method is None:
                next_method = previous_attempt.method

        else:
            next_method = previous_attempt.method

        delay_seconds = self._sample_delay(
            action=action,
            failure_category=(
                previous_attempt.failure_category
            ),
        )

        next_attempt = PaymentAttempt(
            payment_id=(
                f"{journey.order_id}_P"
                f"{next_attempt_number:02d}"
            ),
            attempt_number=next_attempt_number,
            method=next_method,
            attempted_at=(
                previous_attempt.attempted_at
                + timedelta(
                    seconds=delay_seconds
                )
            ),
            status=PaymentStatus.CREATED,
        )

        journey.payment_attempts.append(
            next_attempt
        )

        return next_attempt

    def _continuation_probability(
        self,
        customer: SyntheticCustomer,
        journey: HistoricalJourney,
    ) -> float:
        """Estimate immediate natural continuation after failure."""

        last_attempt = journey.payment_attempts[-1]

        score = (
            1.3
            * (journey.latent_order_propensity - 0.5)
            + 1.1
            * (customer.retry_persistence - 0.5)
            + 0.4
            * (customer.merchant_affinity - 0.5)
            - 0.45
            * (last_attempt.attempt_number - 1)
            + self._failure_continuation_adjustment(
                last_attempt.failure_category
            )
        )

        probability = (
            1.0
            / (1.0 + math.exp(-score))
        )

        return probability

    def _failure_continuation_adjustment(
        self,
        failure_category: FailureCategory | None,
    ) -> float:
        """Adjust continuation based on how correctable the failure appears."""

        adjustments = {
            FailureCategory.AUTHENTICATION_FAILURE: 0.45,
            FailureCategory.TECHNICAL_FAILURE: 0.15,
            FailureCategory.BANK_OR_PROVIDER_UNAVAILABLE: -0.10,
            FailureCategory.INSUFFICIENT_FUNDS: -0.35,
            FailureCategory.LIMIT_EXCEEDED: -0.35,
            FailureCategory.INSTRUMENT_UNAVAILABLE: -0.25,
            FailureCategory.ISSUER_DECLINED: -0.10,
            FailureCategory.RISK_DECLINED: -0.40,
            FailureCategory.USER_CANCELLED: -0.50,
        }

        return adjustments.get(
            failure_category,
            0.0,
        )

    def _choose_active_action(
        self,
        customer: SyntheticCustomer,
        journey: HistoricalJourney,
    ) -> NaturalAction:
        """Choose between retrying the current method and switching."""

        last_attempt = journey.payment_attempts[-1]

        switch_preference = (
            0.10
            + 0.55
            * customer.method_flexibility
        )

        if last_attempt.failure_category in {
            FailureCategory.INSUFFICIENT_FUNDS,
            FailureCategory.LIMIT_EXCEEDED,
            FailureCategory.INSTRUMENT_UNAVAILABLE,
            FailureCategory.BANK_OR_PROVIDER_UNAVAILABLE,
            FailureCategory.TECHNICAL_FAILURE,
        }:
            switch_preference += 0.20

        if (
            last_attempt.failure_category
            == FailureCategory.AUTHENTICATION_FAILURE
        ):
            switch_preference -= 0.20

        switch_preference += (
            0.08
            * (last_attempt.attempt_number - 1)
        )

        switch_preference = max(
            0.02,
            min(0.90, switch_preference),
        )

        available_methods = (
            self.method_selector.get_available_methods(
                customer
            )
        )

        alternate_exists = any(
            method != last_attempt.method
            for method in available_methods
        )

        if (
            alternate_exists
            and self.random.bernoulli(
                switch_preference
            )
        ):
            return NaturalAction.SWITCH_METHOD

        return NaturalAction.RETRY_SAME_METHOD

    def _choose_alternate_method(
        self,
        customer: SyntheticCustomer,
        current_method: PaymentMethod,
    ) -> PaymentMethod | None:
        """Choose one available method different from the failed method."""

        available_methods = [
            method
            for method
            in self.method_selector.get_available_methods(
                customer
            )
            if method != current_method
        ]

        if not available_methods:
            return None

        # Prefer methods the customer is generally comfortable using.
        if (
            customer.habitual_method
            in available_methods
        ):
            if self.random.bernoulli(0.55):
                return customer.habitual_method

        return self.random.choice(
            available_methods
        )

    def _sample_delay(
        self,
        action: NaturalAction,
        failure_category: FailureCategory | None,
    ) -> float:
        """Sample the delay before the customer's next payment attempt."""

        if action == NaturalAction.RETURN_LATER:
            median = (
                self.config.delayed_return_median_seconds
            )

            sigma = (
                self.config.delayed_return_sigma
            )

        elif failure_category in {
            FailureCategory.TECHNICAL_FAILURE,
            FailureCategory.BANK_OR_PROVIDER_UNAVAILABLE,
        }:
            median = (
                self.config.technical_retry_median_seconds
            )

            sigma = (
                self.config.retry_delay_sigma
            )

        else:
            median = (
                self.config.same_method_retry_median_seconds
            )

            sigma = (
                self.config.retry_delay_sigma
            )

        return self.random.lognormal(
            mean=math.log(median),
            sigma=sigma,
        )

    def continuation_probability(
        self,
        customer: SyntheticCustomer,
        journey: HistoricalJourney,
    ) -> float:
        """Return the customer's natural immediate-continuation probability."""

        return self._continuation_probability(
            customer=customer,
            journey=journey,
        )

    def choose_active_action(
        self,
        customer: SyntheticCustomer,
        journey: HistoricalJourney,
    ) -> NaturalAction:
        """Choose what an engaged customer naturally does next."""

        return self._choose_active_action(
            customer=customer,
            journey=journey,
        )