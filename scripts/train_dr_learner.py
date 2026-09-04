"""
Train the second-stage doubly-robust recovery learner.

Input:
    Expanded DR pseudo-outcome dataset.

Output:
    Saved DR model for counterfactual action scoring.
"""

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from ml.dr_learner import (
    DoublyRobustLearner,
)


DATA_PATH = Path(
    "data/dr_training_expanded.csv"
)

MODEL_PATH = Path(
    "models/dr_learner.joblib"
)


print()
print("DOUBLY ROBUST LEARNER TRAINING")
print("==============================")


data = pd.read_csv(
    DATA_PATH
)


print()
print(
    "Training rows:",
    len(data),
)

print(
    "Customers:",
    data[
        "customer_id"
    ].nunique(),
)

print(
    "Candidate treatments:",
    data[
        "candidate_treatment"
    ].nunique(),
)


print()
print("DR TARGET BEFORE TRAINING")
print("-------------------------")

print(
    "Mean:",
    f"{data['dr_pseudo_outcome'].mean():.4f}",
)

print(
    "Minimum:",
    f"{data['dr_pseudo_outcome'].min():.4f}",
)

print(
    "Maximum:",
    f"{data['dr_pseudo_outcome'].max():.4f}",
)


learner = (
    DoublyRobustLearner()
)


print()
print("Training second-stage model...")


learner.fit(
    data
)


print()
print("TRAINING PREDICTION SANITY CHECK")
print("--------------------------------")


predictions = (
    learner.predict_probability(
        data
    )
)


print(
    "Mean prediction:",
    f"{np.mean(predictions):.4f}",
)

print(
    "Minimum prediction:",
    f"{np.min(predictions):.4f}",
)

print(
    "Maximum prediction:",
    f"{np.max(predictions):.4f}",
)


at_zero = int(
    (
        predictions
        <= 0.0
    ).sum()
)

at_one = int(
    (
        predictions
        >= 1.0
    ).sum()
)


print(
    "Predictions clipped at 0:",
    at_zero,
)

print(
    "Predictions clipped at 1:",
    at_one,
)


print()
print("MEAN PREDICTION BY CANDIDATE")
print("----------------------------")


diagnostic = (
    data[
        [
            "candidate_treatment"
        ]
    ]
    .copy()
)

diagnostic[
    "prediction"
] = predictions


summary = (
    diagnostic
    .groupby(
        "candidate_treatment"
    )[
        "prediction"
    ]
    .agg(
        [
            "count",
            "mean",
            "min",
            "max",
        ]
    )
)


print(
    summary.to_string(
        float_format=lambda value:
            f"{value:.4f}"
    )
)


MODEL_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)


joblib.dump(
    learner,
    MODEL_PATH,
)


print()
print(
    "Saved model:",
    MODEL_PATH,
)