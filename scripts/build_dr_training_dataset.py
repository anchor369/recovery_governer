"""
Build the expanded second-stage DR training dataset.

No final DR model is trained here.
"""

from pathlib import Path

import pandas as pd

from ml.crossfit import (
    generate_cross_fitted_predictions,
)
from ml.dr_dataset import (
    build_dr_training_dataset,
)


DATA_PATH = Path(
    "data/historical_recovery.csv"
)

OUTPUT_PATH = Path(
    "data/dr_training_expanded.csv"
)

N_SPLITS = 3


data = pd.read_csv(
    DATA_PATH
)


treatments = sorted(
    data[
        "treatment"
    ].unique()
)


print()
print("BUILDING DR TRAINING DATASET")
print("============================")

print(
    "Original rows:",
    len(data),
)

print(
    "Treatments:",
    len(treatments),
)


print()
print("STEP 1 — CROSS-FITTED FIRST-STAGE PREDICTIONS")
print("---------------------------------------------")


predictions = (
    generate_cross_fitted_predictions(
        dataframe=data,
        treatments=treatments,
        n_splits=N_SPLITS,
    )
)


print()
print("STEP 2 — BUILD DR PSEUDO-OUTCOME ROWS")
print("-------------------------------------")


expanded = (
    build_dr_training_dataset(
        dataframe=data,
        cross_fitted_predictions=(
            predictions
        ),
        treatments=treatments,
    )
)


print(
    "Expanded rows:",
    len(expanded),
)


expected_rows = (
    len(data)
    * len(treatments)
)


print(
    "Expected rows:",
    expected_rows,
)


print()
print("DR TARGET SUMMARY")
print("-----------------")


print(
    "Mean:",
    round(
        expanded[
            "dr_pseudo_outcome"
        ].mean(),
        4,
    ),
)

print(
    "Minimum:",
    round(
        expanded[
            "dr_pseudo_outcome"
        ].min(),
        4,
    ),
)

print(
    "Maximum:",
    round(
        expanded[
            "dr_pseudo_outcome"
        ].max(),
        4,
    ),
)


print()
print("ROWS BY CANDIDATE TREATMENT")
print("---------------------------")


print(
    expanded[
        "candidate_treatment"
    ]
    .value_counts()
    .sort_index()
)


OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)


expanded.to_csv(
    OUTPUT_PATH,
    index=False,
)


print()
print(
    "Saved:",
    OUTPUT_PATH,
)