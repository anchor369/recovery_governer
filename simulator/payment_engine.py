"""
Processes synthetic payment attempts.

The engine separates customer/business failures from infrastructure
failures and produces CAPTURED, FAILED or UNCERTAIN outcomes.
"""

from simulator.config import SimulatorConfig
from simulator.models import (
    FailureCategory,
    HistoricalJourney,
    IncidentMode,
    PaymentAttempt,
    PaymentMethod,
    PaymentStatus,
    SyntheticCustomer,
)
from simulator.payment_environment import PaymentEnvironment
from simulator.random_source import RandomSource


class PaymentEngine:
    """Processes payment attempts using method-specific failure mechanics."""

    def __init__(
        self,
        config: SimulatorConfig,
        random_source: RandomSource,
    ):
        self.config = config
        self.random = random_source

    def process_attempt(
        self,
        customer: SyntheticCustomer,
        journey: HistoricalJourney,
        attempt: PaymentAttempt,
        environment: PaymentEnvironment,
    ) -> PaymentAttempt:
        """Process one payment attempt and update its financial state."""

        if attempt.status != PaymentStatus.CREATED:
            raise ValueError(
                "Only CREATED payment attempts can be processed."
            )

        attempt.observed_rail_health = (environment.observed_health)

        persistent_result = (
            self._process_previous_failure_persistence(
                journey=journey,
                attempt=attempt,
            )
        )

        if persistent_result is not None:
            return persistent_result

        if self._customer_cancelled(
            journey=journey,
            attempt=attempt,
        ):
            return self._fail(
                attempt,
                FailureCategory.USER_CANCELLED,
                "CUSTOMER_CANCELLED_PAYMENT",
                "CUSTOMER",
                "PAYMENT_AUTHENTICATION",
            )

        if attempt.method == PaymentMethod.UPI:
            return self._process_upi(
                customer,
                journey,
                attempt,
                environment,
            )

        if attempt.method == PaymentMethod.CREDIT_CARD:
            return self._process_credit_card(
                customer,
                journey,
                attempt,
                environment,
            )

        if attempt.method == PaymentMethod.DEBIT_CARD:
            return self._process_debit_card(
                customer,
                journey,
                attempt,
                environment,
            )

        return self._process_netbanking(
            customer,
            journey,
            attempt,
            environment,
        )

    def _customer_cancelled(
        self,
        journey: HistoricalJourney,
        attempt: PaymentAttempt,
    ) -> bool:
        """Estimate whether the customer leaves the current payment flow."""

        cancellation_probability = (
            0.004
            + 0.035
            * (1.0 - journey.latent_order_propensity)
            + 0.012
            * (attempt.attempt_number - 1)
        )

        cancellation_probability = min(
            cancellation_probability,
            0.20,
        )

        return self.random.bernoulli(
            cancellation_probability
        )

    def _process_upi(
        self,
        customer,
        journey,
        attempt,
        environment,
    ):
        """Process a UPI attempt."""

        amount_ratio = (
            journey.amount_minor
            / customer.typical_order_value_minor
        )

        insufficient_probability = min(
            0.008 + 0.006 * max(amount_ratio - 1.0, 0.0),
            0.05,
        )

        if self.random.bernoulli(
            insufficient_probability
        ):
            return self._fail(
                attempt,
                FailureCategory.INSUFFICIENT_FUNDS,
                "INSUFFICIENT_BANK_BALANCE",
                "CUSTOMER_BANK",
                "PAYMENT_PROCESSING",
            )

        # ₹1 lakh baseline P2M-style threshold for this synthetic world.
        if journey.amount_minor > 10_000_000:
            return self._fail(
                attempt,
                FailureCategory.LIMIT_EXCEEDED,
                "UPI_TRANSACTION_LIMIT_EXCEEDED",
                "CUSTOMER_BANK",
                "PAYMENT_PROCESSING",
            )

        if self.random.bernoulli(0.016):
            return self._fail(
                attempt,
                FailureCategory.AUTHENTICATION_FAILURE,
                "INCORRECT_UPI_PIN",
                "CUSTOMER",
                "PAYMENT_AUTHENTICATION",
            )

        technical_result = self._process_infrastructure(
            attempt,
            environment,
        )

        if technical_result is not None:
            return technical_result

        if self.random.bernoulli(0.008):
            return self._fail(
                attempt,
                FailureCategory.ISSUER_DECLINED,
                "BANK_DECLINED_PAYMENT",
                "CUSTOMER_BANK",
                "PAYMENT_PROCESSING",
            )

        return self._capture(attempt)

    def _process_credit_card(
        self,
        customer,
        journey,
        attempt,
        environment,
    ):
        """Process a Credit Card attempt."""

        amount_ratio = (
            journey.amount_minor
            / customer.typical_order_value_minor
        )

        if self.random.bernoulli(0.003):
            return self._fail(
                attempt,
                FailureCategory.INSTRUMENT_UNAVAILABLE,
                "CARD_UNAVAILABLE",
                "CUSTOMER",
                "PAYMENT_INITIATION",
            )

        insufficient_probability = min(
            0.012
            + 0.008 * max(amount_ratio - 1.0, 0.0),
            0.06,
        )

        if self.random.bernoulli(
            insufficient_probability
        ):
            return self._fail(
                attempt,
                FailureCategory.INSUFFICIENT_FUNDS,
                "INSUFFICIENT_AVAILABLE_CREDIT",
                "ISSUER_BANK",
                "PAYMENT_PROCESSING",
            )

        if self.random.bernoulli(0.018):
            return self._fail(
                attempt,
                FailureCategory.AUTHENTICATION_FAILURE,
                "CARD_AUTHENTICATION_FAILED",
                "CUSTOMER",
                "PAYMENT_AUTHENTICATION",
            )

        if self.random.bernoulli(0.005):
            return self._fail(
                attempt,
                FailureCategory.RISK_DECLINED,
                "PAYMENT_RISK_CHECK_FAILED",
                "ISSUER_BANK",
                "RISK_CHECK",
            )

        technical_result = self._process_infrastructure(
            attempt,
            environment,
        )

        if technical_result is not None:
            return technical_result

        if self.random.bernoulli(0.025):
            return self._fail(
                attempt,
                FailureCategory.ISSUER_DECLINED,
                "CARD_DECLINED",
                "ISSUER_BANK",
                "PAYMENT_PROCESSING",
            )

        return self._capture(attempt)

    def _process_debit_card(
        self,
        customer,
        journey,
        attempt,
        environment,
    ):
        """Process a Debit Card attempt."""

        amount_ratio = (
            journey.amount_minor
            / customer.typical_order_value_minor
        )

        if self.random.bernoulli(0.004):
            return self._fail(
                attempt,
                FailureCategory.INSTRUMENT_UNAVAILABLE,
                "DEBIT_CARD_UNAVAILABLE",
                "CUSTOMER",
                "PAYMENT_INITIATION",
            )

        insufficient_probability = min(
            0.012
            + 0.008 * max(amount_ratio - 1.0, 0.0),
            0.06,
        )

        if self.random.bernoulli(
            insufficient_probability
        ):
            return self._fail(
                attempt,
                FailureCategory.INSUFFICIENT_FUNDS,
                "INSUFFICIENT_BANK_BALANCE",
                "CUSTOMER_BANK",
                "PAYMENT_PROCESSING",
            )

        if self.random.bernoulli(0.020):
            return self._fail(
                attempt,
                FailureCategory.AUTHENTICATION_FAILURE,
                "CARD_AUTHENTICATION_FAILED",
                "CUSTOMER",
                "PAYMENT_AUTHENTICATION",
            )

        technical_result = self._process_infrastructure(
            attempt,
            environment,
        )

        if technical_result is not None:
            return technical_result

        if self.random.bernoulli(0.020):
            return self._fail(
                attempt,
                FailureCategory.ISSUER_DECLINED,
                "DEBIT_CARD_DECLINED",
                "ISSUER_BANK",
                "PAYMENT_PROCESSING",
            )

        return self._capture(attempt)

    def _process_netbanking(
        self,
        customer,
        journey,
        attempt,
        environment,
    ):
        """Process a Netbanking attempt."""

        amount_ratio = (
            journey.amount_minor
            / customer.typical_order_value_minor
        )

        if self.random.bernoulli(0.020):
            return self._fail(
                attempt,
                FailureCategory.AUTHENTICATION_FAILURE,
                "BANK_AUTHENTICATION_FAILED",
                "CUSTOMER",
                "PAYMENT_AUTHENTICATION",
            )

        insufficient_probability = min(
            0.010
            + 0.007 * max(amount_ratio - 1.0, 0.0),
            0.06,
        )

        if self.random.bernoulli(
            insufficient_probability
        ):
            return self._fail(
                attempt,
                FailureCategory.INSUFFICIENT_FUNDS,
                "INSUFFICIENT_BANK_BALANCE",
                "CUSTOMER_BANK",
                "PAYMENT_PROCESSING",
            )

        technical_result = self._process_infrastructure(
            attempt,
            environment,
        )

        if technical_result is not None:
            return technical_result

        if self.random.bernoulli(0.025):
            return self._fail(
                attempt,
                FailureCategory.ISSUER_DECLINED,
                "BANK_DECLINED_PAYMENT",
                "CUSTOMER_BANK",
                "PAYMENT_PROCESSING",
            )

        return self._capture(attempt)

    def _process_infrastructure(
        self,
        attempt: PaymentAttempt,
        environment: PaymentEnvironment,
    ):
        """Generate failures caused by infrastructure degradation."""

        degradation = 1.0 - environment.true_health

        technical_risk = (
            self.config.technical_baseline_risk
            + self.config.technical_severity_multiplier
            * degradation ** 3
        )

        if not self.random.bernoulli(
            technical_risk
        ):
            return None

        if environment.incident_mode == IncidentMode.LATENCY:
            if self.random.bernoulli(0.55):
                attempt.status = PaymentStatus.UNCERTAIN
                return attempt

            return self._fail(
                attempt,
                FailureCategory.TECHNICAL_FAILURE,
                "PROCESSING_TIMEOUT",
                "PAYMENT_NETWORK",
                "PAYMENT_PROCESSING",
            )

        if (
            environment.incident_mode
            == IncidentMode.PROVIDER_UNAVAILABLE
        ):
            return self._fail(
                attempt,
                FailureCategory.BANK_OR_PROVIDER_UNAVAILABLE,
                "PROVIDER_UNAVAILABLE",
                "PAYMENT_PROVIDER",
                "PAYMENT_PROCESSING",
            )

        return self._fail(
            attempt,
            FailureCategory.TECHNICAL_FAILURE,
            "PAYMENT_PROCESSING_ERROR",
            "PAYMENT_NETWORK",
            "PAYMENT_PROCESSING",
        )

    @staticmethod
    def _capture(
        attempt: PaymentAttempt,
    ) -> PaymentAttempt:
        """Mark an attempt as successfully captured."""

        attempt.status = PaymentStatus.CAPTURED

        attempt.failure_category = None
        attempt.failure_detail = None
        attempt.failure_source = None
        attempt.failure_step = None

        return attempt

    @staticmethod
    def _fail(
        attempt: PaymentAttempt,
        category: FailureCategory,
        detail: str,
        source: str,
        step: str,
    ) -> PaymentAttempt:
        """Mark an attempt as a confirmed failure."""

        attempt.status = PaymentStatus.FAILED

        attempt.failure_category = category
        attempt.failure_detail = detail
        attempt.failure_source = source
        attempt.failure_step = step

        return attempt

    def _process_previous_failure_persistence(
        self,
        journey: HistoricalJourney,
        attempt: PaymentAttempt,
    ) -> PaymentAttempt | None:
        """
        Preserve short-lived failure conditions across immediate retries.

        Persistence is only applied when the customer retries the same payment
        method. Switching methods is allowed to change the underlying path.
        """

        if attempt.attempt_number <= 1:
            return None

        previous_attempt = journey.payment_attempts[-2]

        if (
            previous_attempt.status
            != PaymentStatus.FAILED
        ):
            return None

        if (
            previous_attempt.method
            != attempt.method
        ):
            return None

        persistence_probability = (
            self._failure_persistence_probability(
                previous_attempt.failure_category
            )
        )

        if persistence_probability <= 0.0:
            return None

        if not self.random.bernoulli(
            persistence_probability
        ):
            return None

        return self._fail(
            attempt=attempt,
            category=previous_attempt.failure_category,
            detail=(
                previous_attempt.failure_detail
                or "PERSISTENT_PAYMENT_FAILURE"
            ),
            source=(
                previous_attempt.failure_source
                or "UNKNOWN"
            ),
            step=(
                previous_attempt.failure_step
                or "PAYMENT_PROCESSING"
            ),
        )

    def _failure_persistence_probability(
        self,
        failure_category: FailureCategory | None,
    ) -> float:
        """Return short-term persistence for a same-method retry."""

        persistence = {
            FailureCategory.AUTHENTICATION_FAILURE:
                self.config.authentication_failure_persistence,

            FailureCategory.INSUFFICIENT_FUNDS:
                self.config.insufficient_funds_persistence,

            FailureCategory.LIMIT_EXCEEDED:
                self.config.limit_exceeded_persistence,

            FailureCategory.INSTRUMENT_UNAVAILABLE:
                self.config.instrument_unavailable_persistence,

            FailureCategory.ISSUER_DECLINED:
                self.config.issuer_declined_persistence,

            FailureCategory.RISK_DECLINED:
                self.config.risk_declined_persistence,
        }

        return persistence.get(
            failure_category,
            0.0,
        )