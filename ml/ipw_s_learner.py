"""
Propensity-weighted pooled S-learner.

This uses the same model architecture as the normal S-learner,
but gives training rows different importance based on how likely
their historical action was to be assigned.
"""

import pandas as pd

from ml.propensity import calculate_ipw_weights
from ml.s_learner import (
    ALL_MODEL_FEATURES,
    PooledSLearner,
)


class IPWPooledSLearner(PooledSLearner):
    """
    S-learner trained with inverse propensity weights.
    """

    def fit(
        self,
        dataframe: pd.DataFrame,
    ):
        # Same feature preparation as the normal S-learner.
        prepared = self._prepare_dataframe(
            dataframe
        )

        # Calculate how strongly each historical row should count.
        sample_weights = (
            calculate_ipw_weights(
                dataframe
            )
        )

        self.model.fit(
            prepared[
                ALL_MODEL_FEATURES
            ],
            prepared["recovered"],

            # Pass weights specifically to the classifier
            # inside the sklearn Pipeline.
            classifier__sample_weight=(
                sample_weights
            ),
        )

        return self