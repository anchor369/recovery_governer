"""
Pooled recovery-response model.

The S-learner trains one model over customer/payment state plus the
candidate recovery action. This allows related actions to share data and
supports nonlinear state-action interactions.
"""

import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
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


class PooledSLearner:
    """Estimate P(recovery | observable state, candidate action)."""

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

        classifier = (
            HistGradientBoostingClassifier(
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
                    "classifier",
                    classifier,
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
            prepared["recovered"],
        )

        return self

    def predict_probability(
        self,
        dataframe: pd.DataFrame,
    ):
        """Predict factual or counterfactual recovery probabilities."""

        prepared = self._prepare_dataframe(
            dataframe
        )

        return self.model.predict_proba(
            prepared[
                ALL_MODEL_FEATURES
            ]
        )[:, 1]

    def predict_treatment(
        self,
        dataframe: pd.DataFrame,
        treatment: str,
    ):
        """
        Score the same states under a requested hypothetical treatment.
        """

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
        """Normalize action payload fields read from CSV."""

        prepared = dataframe.copy()

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
        """Convert dataset treatment label into model action features."""

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