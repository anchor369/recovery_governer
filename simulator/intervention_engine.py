"""
Simulates recovery interventions after a confirmed payment failure.

Actions modify specific parts of customer behaviour. They never directly
set a payment to successful; every resulting payment attempt still passes
through the ordinary payment engine.
"""

import copy
import math
from datetime import timedelta

from simulator.config import SimulatorConfig
from simulator.journey_processor import JourneyProcessor
from simulator.models import (
    ActionType,
    FailureCategory,
    HistoricalJourney,
    NaturalAction,
    PaymentAttempt,
    PaymentMethod,
    PaymentStatus,
    RecoveryAction,
    SyntheticCustomer,
)

from simulator.random_source import RandomSource


class InterventionEngine:
    """Runs one recovery action against a failed synthetic journey."""

    def __init__(
        self,
        config: SimulatorConfig,
        random_source: RandomSource,
        journey_processor: JourneyProcessor,
    ):
        self.config = config
        self.random = random_source
        self.processor = journey_processor

    def simulate_action(
        self,
        customer: SyntheticCustomer,
        journey: HistoricalJourney,
        action: RecoveryAction,
    ) -> HistoricalJourney:
        """
        Simulate one recovery action without modifying the original journey.

        A deep copy creates an independent counterfactual branch.
        """

        branch = copy.deepcopy(journey)

        latest_attempt = branch.payment_attempts[-1]

        if latest_attempt.status != PaymentStatus.FAILED:
            raise ValueError(
                "Recovery actions require a confirmed failed payment."
            )

        if action.action_type == ActionType.NO_ACTION:
            self.processor.process_natural_recovery(
                customer=customer,
                journey=branch,
            )

            return branch

        if action.action_type == ActionType.NUDGE:
            self._apply_nudge(
                customer=customer,
                journey=branch,
            )

            return branch

        if action.action_type == ActionType.SWITCH_METHOD:
            self._apply_switch(
                customer=customer,
                journey=branch,
                action=action,
            )

            return branch

        if action.action_type == ActionType.APPROVED_OFFER:
            self._apply_offer(
                customer=customer,
                journey=branch,
                action=action,
            )

            return branch

        raise ValueError(
            f"Unsupported action: {action.action_type}"
        )

    def _apply_nudge(
        self,
        customer: SyntheticCustomer,
        journey: HistoricalJourney,
    ) -> None:
        """
        Increase the chance that the customer re-engages after failure.

        If the nudge does not create extra engagement, ordinary natural
        recovery still remains possible.
        """

        natural_probability = (
            self.processor.natural_recovery
            .continuation_probability(
                customer=customer,
                journey=journey,
            )
        )

        # Highest incremental opportunity occurs when natural engagement
        # is neither almost impossible nor almost guaranteed.
        opportunity = (
            4.0
            * natural_probability
            * (1.0 - natural_probability)
        )

        nudge_uplift = (
            0.18
            * opportunity
            * (
                0.6
                + 0.4
                * customer.merchant_affinity
            )
        )

        # If the nudge itself does not create extra engagement,
        # ordinary natural behaviour still runs afterward.
        #
        # q + (1-q)p = p + uplift
        # therefore q = uplift / (1-p)
        remaining_room = max(
            1.0 - natural_probability,
            1e-9,
        )

        incremental_trigger_probability = min(
            1.0,
            nudge_uplift / remaining_room,
        )

        if self.random.bernoulli(
            incremental_trigger_probability
        ):
            active_action = (
                self.processor.natural_recovery
                .choose_active_action(
                    customer=customer,
                    journey=journey,
                )
            )

            next_attempt = (
                self.processor.natural_recovery
                .create_next_attempt(
                    customer=customer,
                    journey=journey,
                    action=active_action,
                )
            )

            if next_attempt is not None:
                self.processor.process_attempt(
                    customer=customer,
                    journey=journey,
                    attempt=next_attempt,
                )

                self._continue_after_intervention(
                    customer,
                    journey,
                )

                return

        # Nudge did not generate extra immediate engagement.
        # Customer can still behave naturally.
        self.processor.process_natural_recovery(
            customer=customer,
            journey=journey,
        )
    def _apply_switch(
        self,
        customer: SyntheticCustomer,
        journey: HistoricalJourney,
        action: RecoveryAction,
    ) -> None:
        """
        Recommend a specific alternate payment method.

        SWITCH_METHOD does not create customer engagement by itself.
        It changes method choice only when the customer would otherwise
        continue or return naturally.
        """

        target_method = action.target_method

        if target_method is None:
            raise ValueError(
                "SWITCH_METHOD requires a target_method."
            )

        current_attempt = journey.payment_attempts[-1]

        if target_method == current_attempt.method:
            raise ValueError(
                "Switch target must differ from current method."
            )

        # First sample the customer's ordinary behaviour.
        #
        # This preserves the NO_ACTION engagement process.
        natural_action = (
            self.processor.natural_recovery
            .choose_next_action(
                customer=customer,
                journey=journey,
            )
        )

        # If the customer would abandon, a method recommendation alone
        # does not bring them back.
        if natural_action == NaturalAction.ABANDON:
            journey.abandoned = True
            return

        follow_probability = (
            0.10
            + 0.55 * customer.method_flexibility
        )

        if customer.habitual_method == target_method:
            follow_probability += 0.15

        if current_attempt.failure_category in {
            FailureCategory.TECHNICAL_FAILURE,
            FailureCategory.BANK_OR_PROVIDER_UNAVAILABLE,
            FailureCategory.INSTRUMENT_UNAVAILABLE,
            FailureCategory.INSUFFICIENT_FUNDS,
            FailureCategory.LIMIT_EXCEEDED,
        }:
            follow_probability += 0.15

        if (
            current_attempt.failure_category
            == FailureCategory.AUTHENTICATION_FAILURE
        ):
            follow_probability -= 0.10

        follow_probability = max(
            0.05,
            min(0.90, follow_probability),
        )

        # The recommendation changes method selection only.
        if self.random.bernoulli(
            follow_probability
        ):
            delay_seconds = (
                self._switch_delay_seconds(
                    natural_action
                )
            )

            next_attempt = self._create_targeted_attempt(
                journey=journey,
                target_method=target_method,
                delay_seconds=delay_seconds,
            )

        else:
            # Recommendation was ignored.
            # Preserve whatever the customer would naturally have done.
            next_attempt = (
                self.processor.natural_recovery
                .create_next_attempt(
                    customer=customer,
                    journey=journey,
                    action=natural_action,
                )
            )

        if next_attempt is None:
            return

        self.processor.process_attempt(
            customer=customer,
            journey=journey,
            attempt=next_attempt,
        )

        self._continue_after_intervention(
            customer=customer,
            journey=journey,
        )

    def _switch_delay_seconds(
        self,
        natural_action: NaturalAction,
    ) -> float:
        """
        Preserve whether the customer's next attempt was immediate or delayed.
        """

        if natural_action == NaturalAction.RETURN_LATER:
            return self.random.lognormal(
                mean=math.log(
                    self.config.delayed_return_median_seconds
                ),
                sigma=self.config.delayed_return_sigma,
            )

        return 30.0

    def _apply_offer(
        self,
        customer: SyntheticCustomer,
        journey: HistoricalJourney,
        action: RecoveryAction,
    ) -> None:
        """
        Apply an approved discount while preserving the Order's existing
        latent behavioural state.
        """

        discount_percent = action.discount_percent

        if discount_percent is None:
            raise ValueError(
                "APPROVED_OFFER requires discount_percent."
            )

        discount_fraction = (
            discount_percent / 100.0
        )

        if not 0.0 < discount_fraction < 1.0:
            raise ValueError(
                "Discount must be between 0 and 100 percent."
            )

        effective_amount_minor = (
            journey.amount_minor
            * (1.0 - discount_fraction)
        )

        # Recover the existing latent score rather than resampling its noise.
        original_probability = max(
            1e-6,
            min(
                1.0 - 1e-6,
                journey.latent_order_propensity,
            ),
        )

        original_logit = math.log(
            original_probability
            / (1.0 - original_probability)
        )

        # This is exactly the reduction in the price-pressure term caused
        # by lowering the effective price.
        price_relief = (
            self.config.price_pressure_weight
            * customer.price_sensitivity
            * math.log(
                journey.amount_minor
                / effective_amount_minor
            )
        )

        adjusted_logit = (
            original_logit
            + price_relief
        )

        journey.latent_order_propensity = (
            1.0
            / (
                1.0
                + math.exp(-adjusted_logit)
            )
        )

        self.processor.process_natural_recovery(
            customer=customer,
            journey=journey,
        )
    def _create_targeted_attempt(
        self,
        journey: HistoricalJourney,
        target_method: PaymentMethod,
        delay_seconds: float,
    ) -> PaymentAttempt:
        """Create a payment attempt using a specific target method."""

        previous_attempt = (
            journey.payment_attempts[-1]
        )

        next_attempt_number = (
            previous_attempt.attempt_number + 1
        )

        if (
            next_attempt_number
            > self.config.max_payment_attempts
        ):
            journey.abandoned = True

            raise RuntimeError(
                "Recovery action exceeded maximum payment attempts."
            )

        next_attempt = PaymentAttempt(
            payment_id=(
                f"{journey.order_id}_P"
                f"{next_attempt_number:02d}"
            ),
            attempt_number=next_attempt_number,
            method=target_method,
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

    def _continue_after_intervention(
        self,
        customer: SyntheticCustomer,
        journey: HistoricalJourney,
    ) -> None:
        """Allow ordinary natural behaviour after the intervention attempt."""

        latest_attempt = journey.payment_attempts[-1]

        if latest_attempt.status == PaymentStatus.CAPTURED:
            return

        if latest_attempt.status == PaymentStatus.UNCERTAIN:
            return

        self.processor.process_natural_recovery(
            customer=customer,
            journey=journey,
        )

    