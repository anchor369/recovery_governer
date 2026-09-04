"""
Features describing a candidate recovery action for a specific state.

These features are derived only from information observable at decision
time. Hidden simulator traits must never be used here.
"""

import pandas as pd


METHOD_COUNT_COLUMNS = {
    "UPI": "prior_upi_count",
    "CREDIT_CARD": "prior_credit_card_count",
    "DEBIT_CARD": "prior_debit_card_count",
    "NETBANKING": "prior_netbanking_count",
}


METHOD_AVAILABILITY_COLUMNS = {
    "UPI": "available_upi",
    "CREDIT_CARD": "available_credit_card",
    "DEBIT_CARD": "available_debit_card",
    "NETBANKING": "available_netbanking",
}


def add_candidate_features(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add features describing the candidate target payment method.

    For non-switch actions, target-specific features are zero.
    """

    result = dataframe.copy()

    target_usage_counts = []
    target_available_values = []

    for _, row in result.iterrows():

        target_method = row.get(
            "target_method",
            "NONE",
        )

        if pd.isna(target_method):
            target_method = "NONE"

        target_method = str(
            target_method
        )

        count_column = (
            METHOD_COUNT_COLUMNS.get(
                target_method
            )
        )

        availability_column = (
            METHOD_AVAILABILITY_COLUMNS.get(
                target_method
            )
        )

        if count_column is None:
            target_usage_count = 0.0
        else:
            target_usage_count = float(
                row[count_column]
            )

        if availability_column is None:
            target_available = 0.0
        else:
            target_available = float(
                row[availability_column]
            )

        target_usage_counts.append(
            target_usage_count
        )

        target_available_values.append(
            target_available
        )

    result[
        "target_prior_usage_count"
    ] = target_usage_counts

    total_prior_method_usage = (
        result["prior_upi_count"]
        + result["prior_credit_card_count"]
        + result["prior_debit_card_count"]
        + result["prior_netbanking_count"]
    )

    result[
        "target_prior_usage_share"
    ] = 0.0

    has_history = (
        total_prior_method_usage > 0
    )

    result.loc[
        has_history,
        "target_prior_usage_share",
    ] = (
        result.loc[
            has_history,
            "target_prior_usage_count",
        ]
        /
        total_prior_method_usage[
            has_history
        ]
    )

    result[
        "target_available"
    ] = target_available_values

    return result