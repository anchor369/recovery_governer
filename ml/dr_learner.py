"""
Second-stage doubly-robust recovery learner.

The model learns smoothed counterfactual outcome estimates from
cross-fitted doubly-robust pseudo-outcomes.
"""

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from ml.features import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
)


ACTION_NUMERIC_FEATURES = [
    "discount_percent",
]


ACTION_CATEGORICAL_FEATURES = [
    "action_type",
    "target_method",
]


ALL_NUMERIC_FEATURES = (
    NUMERIC_FEATURES
    + ACTION_NUMERIC_FEATURES
)


ALL_CATEGORICAL_FEATURES = (
    CATEGORICAL_FEATURES
    + ACTION_CATEGORICAL_FEATURES
)


ALL_MODEL_FEATURES = (
    ALL_NUMERIC_FEATURES
    + ALL_CATEGORICAL_FEATURES
)


class DoublyRobustLearner:
    """
    Learn E[DR pseudo-outcome | state, candidate action].
    """

    def __init__(self):
        self.model = self._build_model()

    @staticmethod
    def _build_model():

        preprocessing = ColumnTransformer(
            transformers=[
                (
                    "numeric",
                    "passthrough",
                    ALL_NUMERIC_FEATURES,
                ),
                (
                    "categorical",
                    OneHotEncoder(
                        handle_unknown="ignore",
                        sparse_output=False,
                    ),
                    ALL_CATEGORICAL_FEATURES,
                ),
            ]
        )

        regressor = (
            HistGradientBoostingRegressor(
                learning_rate=0.05,
                max_iter=250,
                max_leaf_nodes=15,
                min_samples_leaf=40,
                l2_regularization=1.0,
                random_state=42,
            )
        )

        return Pipeline(
            steps=[
                (
                    "preprocessing",
                    preprocessing,
                ),
                (
                    "regressor",
                    regressor,
                ),
            ]
        )

    def fit(
        self,
        dataframe: pd.DataFrame,
    ):

        prepared = self._prepare_dataframe(
            dataframe
        )

        self.model.fit(
            prepared[
                ALL_MODEL_FEATURES
            ],
            prepared[
                "dr_pseudo_outcome"
            ],
        )

        return self

    def predict_probability(
        self,
        dataframe: pd.DataFrame,
    ):
        """
        Predict recovery probability.

        The regression target may exceed [0, 1], but final recovery
        predictions are constrained to the valid probability range.
        """

        prepared = self._prepare_dataframe(
            dataframe
        )

        predictions = (
            self.model.predict(
                prepared[
                    ALL_MODEL_FEATURES
                ]
            )
        )

        return np.clip(
            predictions,
            0.0,
            1.0,
        )

    def predict_treatment(
        self,
        dataframe: pd.DataFrame,
        treatment: str,
    ):

        counterfactual = (
            dataframe.copy()
        )

        (
            action_type,
            target_method,
            discount_percent,
        ) = self._decode_treatment(
            treatment
        )

        counterfactual[
            "action_type"
        ] = action_type

        counterfactual[
            "target_method"
        ] = target_method

        counterfactual[
            "discount_percent"
        ] = discount_percent

        return self.predict_probability(
            counterfactual
        )

    @staticmethod
    def _prepare_dataframe(
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:

        prepared = (
            dataframe.copy()
        )

        prepared[
            "target_method"
        ] = (
            prepared[
                "target_method"
            ]
            .fillna("NONE")
            .replace("", "NONE")
        )

        prepared[
            "discount_percent"
        ] = (
            pd.to_numeric(
                prepared[
                    "discount_percent"
                ],
                errors="coerce",
            )
            .fillna(0.0)
        )

        return prepared

    @staticmethod
    def _decode_treatment(
        treatment: str,
    ):

        if treatment == "NO_ACTION":
            return (
                "NO_ACTION",
                "NONE",
                0.0,
            )

        if treatment == "NUDGE":
            return (
                "NUDGE",
                "NONE",
                0.0,
            )

        if treatment.startswith(
            "OFFER_"
        ):

            percentage = float(
                treatment.split(
                    "_",
                    maxsplit=1,
                )[1]
            )

            return (
                "APPROVED_OFFER",
                "NONE",
                percentage,
            )

        if treatment.startswith(
            "SWITCH_"
        ):

            target_method = (
                treatment.removeprefix(
                    "SWITCH_"
                )
            )

            return (
                "SWITCH_METHOD",
                target_method,
                0.0,
            )

        raise ValueError(
            f"Unknown treatment: {treatment}"
        )