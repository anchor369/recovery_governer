"""
Treatment-specific recovery probability models.

One model is trained per historical recovery treatment. Together these
models estimate P(recovery | X, treatment) for counterfactual scoring.
"""

from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    OneHotEncoder,
    StandardScaler,
)

from ml.features import (
    CATEGORICAL_FEATURES,
    MODEL_FEATURES,
    NUMERIC_FEATURES,
)


class TreatmentLearner:
    """Simple T-learner with one probability model per treatment."""

    def __init__(self):
        self.models = {}

    def _build_model(self):
        preprocessing = ColumnTransformer(
            transformers=[
                (
                    "numeric",
                    StandardScaler(),
                    NUMERIC_FEATURES,
                ),
                (
                    "categorical",
                    OneHotEncoder(
                        handle_unknown="ignore",
                    ),
                    CATEGORICAL_FEATURES,
                ),
            ]
        )

        classifier = LogisticRegression(
            max_iter=2000,
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
        dataframe,
    ):
        """Train one recovery model for every observed treatment."""

        self.models = {}

        treatments = sorted(
            dataframe["treatment"].unique()
        )

        for treatment in treatments:

            treatment_data = dataframe[
                dataframe["treatment"]
                == treatment
            ]

            model = self._build_model()

            model.fit(
                treatment_data[
                    MODEL_FEATURES
                ],
                treatment_data["recovered"],
            )

            self.models[
                treatment
            ] = model

        return self

    def predict_probability(
        self,
        dataframe,
        treatment,
    ):
        """Estimate recovery probability under one treatment."""

        if treatment not in self.models:
            raise ValueError(
                f"No model trained for treatment: {treatment}"
            )

        model = self.models[
            treatment
        ]

        return model.predict_proba(
            dataframe[
                MODEL_FEATURES
            ]
        )[:, 1]

    def predict_all_treatments(
        self,
        dataframe,
    ):
        """Return counterfactual recovery probabilities for all treatments."""

        predictions = {}

        for treatment in sorted(
            self.models
        ):
            predictions[
                treatment
            ] = self.predict_probability(
                dataframe=dataframe,
                treatment=treatment,
            )

        return predictions