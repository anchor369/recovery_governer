import uuid
from datetime import (
    datetime,
    timedelta,
    timezone,
)

from backend.data_access.payments import (
    create_customer,
    create_order,
    create_payment,
    record_payment_event,
)

from backend.services.payment_truth import (
    evaluate_order_truth,
    evaluate_order_truth_at_time,
)

from backend.services.recovery_eligibility import (
    evaluate_recovery_eligibility,
)

from backend.services.recovery_engine import (
    run_recovery_workflow,
)

from backend.services.recovery_factory import (
    create_recovery_decision_service,
)

from backend.services.recovery_outcome import (
    record_recovered_payment,
)

from backend.services.recovery_state import (
    RuntimeRecoverySignals,
)

from simulator.models import (
    ActionType,
)

from simulator.action_codec import (
    action_to_label,
)

def rupees(minor_value):
    return (
        minor_value
        / 100.0
    )


def recovery_payment_method(
    chosen_action,
    state,
):
    """
    Decide which payment method the simulated
    customer uses after the recovery action.

    SWITCH_METHOD:
        use the Governor's target method.

    NUDGE / OFFER / NO_ACTION:
        retry the current payment method.
    """

    if (
        chosen_action.action_type
        == ActionType.SWITCH_METHOD
        and chosen_action.target_method
        is not None
    ):
        return (
            chosen_action
            .target_method
            .value
        )

    return state.current_method.value


suffix = uuid.uuid4().hex[:8]

customer_id = (
    f"C_SMOKE_{suffix}"
)

prior_order_id = (
    f"O_SMOKE_PRIOR_{suffix}"
)

current_order_id = (
    f"O_SMOKE_CURRENT_{suffix}"
)

prior_payment_id = (
    f"P_SMOKE_PRIOR_{suffix}"
)

current_payment_1 = (
    f"P_SMOKE_CURRENT_1_{suffix}"
)

current_payment_2 = (
    f"P_SMOKE_CURRENT_2_{suffix}"
)

recovery_payment_id = (
    f"P_SMOKE_RECOVERED_{suffix}"
)


print()
print(
    "CREATING OPERATIONAL RECOVERY SCENARIO"
)
print(
    "======================================"
)


# --------------------------------------------------
# 1. CUSTOMER
# --------------------------------------------------

create_customer(
    customer_id=customer_id,
    contact_consent=True,
)


# --------------------------------------------------
# 2. PRIOR SUCCESSFUL ORDER
# --------------------------------------------------

create_order(
    order_id=prior_order_id,
    customer_id=customer_id,
    amount_minor=100_000,
)

create_payment(
    payment_id=prior_payment_id,
    order_id=prior_order_id,
    method="UPI",
    status="CAPTURED",
)


# --------------------------------------------------
# 3. CURRENT ORDER WITH TWO FAILED ATTEMPTS
# --------------------------------------------------

create_order(
    order_id=current_order_id,
    customer_id=customer_id,
    amount_minor=150_000,
)

create_payment(
    payment_id=current_payment_1,
    order_id=current_order_id,
    method="UPI",
    status="FAILED",
    failure_reason=(
        "AUTHENTICATION_FAILURE"
    ),
)

create_payment(
    payment_id=current_payment_2,
    order_id=current_order_id,
    method="NETBANKING",
    status="FAILED",
    failure_reason=(
        "TECHNICAL_FAILURE"
    ),
)


now = datetime.now(
    timezone.utc
)


# --------------------------------------------------
# 4. PAYMENT EVENT HISTORY
# --------------------------------------------------

record_payment_event(
    payment_id=prior_payment_id,
    provider_event_id=(
        f"EV_SMOKE_PRIOR_{suffix}"
    ),
    event_type="CAPTURED",
    event_time=(
        now
        - timedelta(minutes=20)
    ),
)

record_payment_event(
    payment_id=current_payment_1,
    provider_event_id=(
        f"EV_SMOKE_FAIL_1_{suffix}"
    ),
    event_type="FAILED",
    event_time=(
        now
        - timedelta(minutes=10)
    ),
)

record_payment_event(
    payment_id=current_payment_2,
    provider_event_id=(
        f"EV_SMOKE_FAIL_2_{suffix}"
    ),
    event_type="FAILED",
    event_time=(
        now
        - timedelta(minutes=5)
    ),
)


decision_time = (
    now
    + timedelta(seconds=5)
)


# --------------------------------------------------
# 5. FINANCIAL TRUTH + ELIGIBILITY
# --------------------------------------------------

print()
print(
    "FINANCIAL TRUTH"
)
print(
    "==============="
)

print(
    "Order:",
    current_order_id,
)

print(
    "Current truth:",
    evaluate_order_truth(
        current_order_id
    ),
)

print(
    "Truth as-of decision:",
    evaluate_order_truth_at_time(
        order_id=current_order_id,
        before_time=decision_time,
    ),
)


eligibility = (
    evaluate_recovery_eligibility(
        current_order_id
    )
)

print(
    "Eligibility:",
    eligibility,
)


# --------------------------------------------------
# 6. RUNTIME SIGNALS
# --------------------------------------------------

signals = RuntimeRecoverySignals(
    available_upi=True,
    available_credit_card=True,
    available_debit_card=True,
    available_netbanking=True,

    observed_rail_health=0.80,

    customer_active=False,
)


# --------------------------------------------------
# 7. REAL MODEL + GOVERNOR
# --------------------------------------------------

decision_service = (
    create_recovery_decision_service()
)


result = run_recovery_workflow(
    order_id=current_order_id,
    decision_time=decision_time,
    runtime_signals=signals,
    decision_service=decision_service,
)


print()
print(
    "WORKFLOW RESULT"
)
print(
    "==============="
)

print(
    "Workflow state:",
    result.workflow_state,
)

print(
    "Reason:",
    result.reason,
)

print(
    "Recovery case:",
    result.case,
)


if result.decision is None:
    print(
        "No ML/Governor decision was made."
    )

else:
    operational_decision = (
        result.decision
    )

    state = (
        operational_decision.state
    )

    governor_decision = (
        operational_decision
        .governor_decision
    )


    # ----------------------------------------------
    # 8. OBSERVABLE MODEL STATE
    # ----------------------------------------------

    print()
    print(
        "OBSERVABLE DECISION STATE"
    )
    print(
        "========================="
    )

    print(
        "Current method:",
        state.current_method.value,
    )

    print(
        "Failure category:",
        state.failure_category.value,
    )

    print(
        "Attempt count:",
        state.attempt_count,
    )

    print(
        "Prior checkouts:",
        state.prior_checkout_count,
    )

    print(
        "Prior successes:",
        state.prior_success_count,
    )

    print(
        "Amount ratio:",
        round(
            state.amount_ratio,
            3,
        ),
    )

    print(
        "Contact consent:",
        state.contact_consent,
    )

    print(
        "Customer active:",
        state.customer_active,
    )


    # ----------------------------------------------
    # 9. GOVERNOR SCORES
    # ----------------------------------------------

    print()
    print(
        "CANDIDATE SCORES"
    )
    print(
        "================"
    )

    for score in (
        governor_decision.scores
    ):
        label = action_to_label(
            score.action
        )

        print()
        print(label)

        print(
            "  Predicted recovery:",
            (
                f"{score.predicted_recovery_probability * 100:.2f}%"
            ),
        )

        print(
            "  Expected merchant value:",
            (
                f"₹{rupees(score.expected_value_minor):.2f}"
            ),
        )

        print(
            "  Incremental utility:",
            (
                f"₹{rupees(score.incremental_utility_minor):+.2f}"
            ),
        )


    chosen = (
        governor_decision
        .chosen_action
    )


    print()
    print(
        "FINAL GOVERNOR DECISION"
    )
    print(
        "======================="
    )

    print(
        "Chosen action:",
        action_to_label(
            chosen
        ),
    )


    # ----------------------------------------------
    # 10. AUDIT PERSISTENCE
    # ----------------------------------------------

    print()
    print(
        "DECISION AUDIT"
    )
    print(
        "=============="
    )

    print(
        "Decision ID:",
        result.audit[
            "decision"
        ][
            "decision_id"
        ],
    )

    print(
        "Stored candidate scores:",
        len(
            result.audit[
                "scores"
            ]
        ),
    )


    # ----------------------------------------------
    # 11. ACTION EXECUTION
    # ----------------------------------------------

    print()
    print(
        "RECOVERY ACTION"
    )
    print(
        "==============="
    )

    print(
        "Action ID:",
        result.action[
            "action_id"
        ],
    )

    print(
        "Action type:",
        result.action[
            "action_type"
        ],
    )

    print(
        "Execution status:",
        result.action[
            "execution_status"
        ],
    )

    print(
        "Blocked reason:",
        result.action[
            "blocked_reason"
        ],
    )

    print(
        "Executed at:",
        result.action[
            "executed_at"
        ],
    )


    # ----------------------------------------------
    # 12. SIMULATE CUSTOMER RECOVERY
    # ----------------------------------------------

    if (
        result.action[
            "execution_status"
        ]
        in {
            "EXECUTED",
            "NOT_REQUIRED",
        }
    ):
        payment_method = (
            recovery_payment_method(
                chosen_action=chosen,
                state=state,
            )
        )

        recovery_time = (
            datetime.now(
                timezone.utc
            )
        )

        print()
        print(
            "SIMULATING POST-ACTION PAYMENT"
        )
        print(
            "=============================="
        )

        print(
            "Recovery payment:",
            recovery_payment_id,
        )

        print(
            "Payment method:",
            payment_method,
        )


        create_payment(
            payment_id=(
                recovery_payment_id
            ),
            order_id=(
                current_order_id
            ),
            method=(
                payment_method
            ),
            status="CAPTURED",
            failure_reason=None,
        )


        record_payment_event(
            payment_id=(
                recovery_payment_id
            ),
            provider_event_id=(
                f"EV_SMOKE_RECOVERED_{suffix}"
            ),
            event_type="CAPTURED",
            event_time=(
                recovery_time
            ),
        )


        print(
            "Truth after CAPTURED event:",
            evaluate_order_truth(
                current_order_id
            ),
        )


        # ------------------------------------------
        # 13. RECORD VERIFIED OUTCOME
        # ------------------------------------------

        outcome_result = (
            record_recovered_payment(
                recovery_case_id=(
                    result.case[
                        "recovery_case_id"
                    ]
                ),
                action_id=(
                    result.action[
                        "action_id"
                    ]
                ),
                payment_id=(
                    recovery_payment_id
                ),
                outcome_time=(
                    recovery_time
                ),
            )
        )


        print()
        print(
            "RECOVERY OUTCOME"
        )
        print(
            "================"
        )

        print(
            "Outcome ID:",
            outcome_result[
                "outcome"
            ][
                "outcome_id"
            ],
        )

        print(
            "Outcome type:",
            outcome_result[
                "outcome"
            ][
                "outcome_type"
            ],
        )

        print(
            "Payment ID:",
            outcome_result[
                "outcome"
            ][
                "payment_id"
            ],
        )

        print(
            "Recovered amount:",
            (
                f"₹{rupees(
                    outcome_result[
                        'outcome'
                    ][
                        'recovered_amount_minor'
                    ]
                ):.2f}"
            ),
        )

        print(
            "Time to recovery:",
            (
                outcome_result[
                    "outcome"
                ][
                    "time_to_recovery_seconds"
                ]
            ),
            "seconds",
        )


        # ------------------------------------------
        # 14. CASE CLOSURE
        # ------------------------------------------

        print()
        print(
            "FINAL RECOVERY CASE"
        )
        print(
            "==================="
        )

        print(
            "Status:",
            outcome_result[
                "case"
            ][
                "status"
            ],
        )

        print(
            "Closure reason:",
            outcome_result[
                "case"
            ][
                "closure_reason"
            ],
        )

        print(
            "Closed at:",
            outcome_result[
                "case"
            ][
                "closed_at"
            ],
        )


        print()
        print(
            "COMPLETE LIFECYCLE"
        )
        print(
            "=================="
        )

        print(
            "FAILED x2"
        )

        print(
            "    ↓"
        )

        print(
            "RECOVERY CASE"
        )

        print(
            "    ↓"
        )

        print(
            "ML + ECONOMIC GOVERNOR"
        )

        print(
            "    ↓"
        )

        print(
            action_to_label(
                chosen
            )
        )

        print(
            "    ↓"
        )

        print(
            "EXECUTED"
        )

        print(
            "    ↓"
        )

        print(
            "CAPTURED PAYMENT"
        )

        print(
            "    ↓"
        )

        print(
            "RECOVERED"
        )

        print(
            "    ↓"
        )

        print(
            "CASE CLOSED"
        )

    else:
        print()
        print(
            "Action was not executed."
        )

        print(
            "No recovered payment is "
            "simulated."
        )