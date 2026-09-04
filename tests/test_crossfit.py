import pandas as pd

from ml.crossfit import (
    generate_cross_fitted_predictions,
)


def build_dataframe():

    rows = []

    for customer_index in range(12):

        for order_index in range(2):

            index = (
                customer_index * 2
                + order_index
            )

            rows.append(
                {
                    "customer_id":
                        f"C{customer_index}",

                    "customer_tenure_days":
                        100 + index,

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

                    "current_amount_minor":
                        100000 + index,

                    "amount_ratio": 1.0,
                    "attempt_count": 1,

                    "observed_rail_health": 0.9,
                    "contact_consent": True,
                    "customer_active": False,

                    "current_method": "UPI",

                    "failure_category":
                        "ISSUER_DECLINED",

                    "action_type": (
                        "NO_ACTION"
                        if index % 2 == 0
                        else "NUDGE"
                    ),

                    "target_method": "NONE",
                    "discount_percent": 0.0,

                    "recovered":
                        index % 2,
                }
            )

    return pd.DataFrame(
        rows
    )


def test_crossfit_returns_prediction_for_every_row():

    dataframe = build_dataframe()

    predictions = (
        generate_cross_fitted_predictions(
            dataframe=dataframe,
            treatments=[
                "NO_ACTION",
                "NUDGE",
            ],
            n_splits=3,
        )
    )

    assert (
        len(
            predictions[
                "NO_ACTION"
            ]
        )
        == len(dataframe)
    )

    assert (
        len(
            predictions[
                "NUDGE"
            ]
        )
        == len(dataframe)
    )


def test_crossfit_probabilities_are_valid():

    dataframe = build_dataframe()

    predictions = (
        generate_cross_fitted_predictions(
            dataframe=dataframe,
            treatments=[
                "NO_ACTION",
                "NUDGE",
            ],
            n_splits=3,
        )
    )

    for treatment_predictions in (
        predictions.values()
    ):

        assert (
            treatment_predictions
            >= 0
        ).all()

        assert (
            treatment_predictions
            <= 1
        ).all()