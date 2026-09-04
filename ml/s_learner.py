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
from ml.action_features import (
    CANDIDATE_METHOD_HISTORY_FEATURES,
    add_candidate_method_history_features,
)

from ml.features import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
)
from simulator.action_codec import (
    treatment_label_to_features,
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

    def __init__(
            self,
            extra_numeric_features=None,
            use_candidate_method_history=False
        ):
        self.extra_numeric_features = list(
            extra_numeric_features or []
        )
        self.use_candidate_method_history = (
            use_candidate_method_history
        )
        self.model = self._build_model()

    def _all_numeric_features(self):
        extra_features = getattr(
            self,
            "extra_numeric_features",
            [],
        )

        use_candidate_history = getattr(
            self,
            "use_candidate_method_history",
            False,
        )

        candidate_features = []

        if use_candidate_history:
            candidate_features = (
                CANDIDATE_METHOD_HISTORY_FEATURES
            )

        return (
            NUMERIC_FEATURES
            + extra_features
            + candidate_features
            + ACTION_NUMERIC_FEATURES
        )


    def _all_model_features(self):
        return (
            self._all_numeric_features()
            + ALL_CATEGORICAL_FEATURES
        )
    def _build_model(self):
        preprocessing = ColumnTransformer(
            transformers=[
                (
                    "numeric",
                    "passthrough",
                    self._all_numeric_features(),
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
                self._all_model_features()
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
                self._all_model_features()
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
        ) = treatment_label_to_features(
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
    def _prepare_dataframe(
        self,
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
        use_candidate_history = getattr(
            self,
            "use_candidate_method_history",
            False,
        )

        if use_candidate_history:
            prepared = (
                add_candidate_method_history_features(
                    prepared
                )
            )
        return prepared
