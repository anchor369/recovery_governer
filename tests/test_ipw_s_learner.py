import pandas as pd

from ml.ipw_s_learner import (
    IPWPooledSLearner,
)


def test_ipw_s_learner_can_fit():

    rows = []

    for index in range(100):

        recovered = (
            index % 2
        )

        rows.append(
            {
                "customer_tenure_days": 100 + index,
                "prior_checkout_count": 5,
                "prior_success_count": 3,
                "prior_failure_count": 2,
                "prior_success_rate": 0.6,

                "prior_upi_count": 3,
                "prior_credit_card_count": 1,
                "prior_debit_card_count": 1,
                "prior_netbanking_count": 0,

                "available_upi": True,
                "available_credit_card": True,
                "available_debit_card": True,
                "available_netbanking": True,

                "current_amount_minor": 100000,
                "amount_ratio": 1.0,
                "attempt_count": 1,

                "observed_rail_health": 0.9,
                "contact_consent": True,
                "customer_active": False,

                "current_method": "UPI",
                "failure_category": "ISSUER_DECLINED",

                "action_type": (
                    "NO_ACTION"
                    if index % 2 == 0
                    else "NUDGE"
                ),

                "target_method": "NONE",
                "discount_percent": 0.0,

                "behavior_policy_probability": (
                    0.50
                    if index % 2 == 0
                    else 0.10
                ),

                "recovered": recovered,
            }
        )

    dataframe = pd.DataFrame(
        rows
    )

    learner = (
        IPWPooledSLearner()
    )

    learner.fit(
        dataframe
    )

    probabilities = (
        learner.predict_probability(
            dataframe
        )
    )

    assert (
        len(probabilities)
        == len(dataframe)
    )