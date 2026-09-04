"""
Cross-fitting helpers for causal recovery models.

Each historical row receives predictions from a model that did not
train on that row or on other rows from the same customer.
"""

import numpy as np
import pandas as pd

from sklearn.model_selection import GroupKFold

from ml.s_learner import PooledSLearner


def generate_cross_fitted_predictions(
    dataframe: pd.DataFrame,
    treatments: list[str],
    n_splits: int = 3,
) -> dict[str, np.ndarray]:
    """
    Generate out-of-fold predictions for every treatment.
    """

    if "customer_id" not in dataframe.columns:
        raise ValueError(
            "customer_id is required for grouped cross-fitting."
        )

    # Create empty prediction arrays.
    # One array for every possible treatment.
    predictions = {
        treatment: np.zeros(
            len(dataframe),
            dtype=float,
        )
        for treatment in treatments
    }

    # We split using customer_id so one customer's rows
    # cannot appear in both train and validation.
    groups = dataframe[
        "customer_id"
    ].to_numpy()

    splitter = GroupKFold(
        n_splits=n_splits
    )

    for fold_number, (
        train_indices,
        validation_indices,
    ) in enumerate(
        splitter.split(
            dataframe,
            groups=groups,
        ),
        start=1,
    ):

        print(
            f"Cross-fitting fold "
            f"{fold_number}/{n_splits}"
        )

        # Data the temporary model IS allowed to learn from.
        fold_train = dataframe.iloc[
            train_indices
        ]

        # Data the temporary model has NEVER seen.
        fold_validation = dataframe.iloc[
            validation_indices
        ]

        learner = PooledSLearner()

        learner.fit(
            fold_train
        )

        # Ask this temporary model:
        # "What would happen under every treatment?"
        for treatment in treatments:

            fold_predictions = (
                learner.predict_treatment(
                    dataframe=fold_validation,
                    treatment=treatment,
                )
            )

            # Put predictions back into their original row positions.
            predictions[
                treatment
            ][
                validation_indices
            ] = fold_predictions

    return predictions