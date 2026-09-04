from pathlib import Path

import joblib
import pandas as pd

from sklearn.metrics import (
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.model_selection import (
    GroupShuffleSplit,
)

from ml.t_learner import TreatmentLearner


DATA_PATH = Path(
    "data/historical_recovery.csv"
)

MODEL_PATH = Path(
    "models/t_learner.joblib"
)


data = pd.read_csv(
    DATA_PATH
)


# Split by CUSTOMER, not random row.
#
# Otherwise historical decisions from the same customer could appear
# in both train and test sets.
splitter = GroupShuffleSplit(
    n_splits=1,
    test_size=0.20,
    random_state=42,
)


train_indices, test_indices = next(
    splitter.split(
        data,
        groups=data["customer_id"],
    )
)


train_data = (
    data.iloc[train_indices]
    .reset_index(drop=True)
)

test_data = (
    data.iloc[test_indices]
    .reset_index(drop=True)
)


print()
print("T-LEARNER TRAINING")
print("------------------")

print(
    "Training rows:",
    len(train_data),
)

print(
    "Test rows:",
    len(test_data),
)

print(
    "Train customers:",
    train_data[
        "customer_id"
    ].nunique(),
)

print(
    "Test customers:",
    test_data[
        "customer_id"
    ].nunique(),
)


learner = TreatmentLearner()

learner.fit(
    train_data
)


print()
print("HELD-OUT FACTUAL PERFORMANCE")
print("----------------------------")


for treatment in sorted(
    learner.models
):

    treatment_test = test_data[
        test_data["treatment"]
        == treatment
    ]

    if len(treatment_test) < 20:
        continue

    probabilities = (
        learner.predict_probability(
            dataframe=treatment_test,
            treatment=treatment,
        )
    )

    labels = treatment_test[
        "recovered"
    ].to_numpy()

    brier = brier_score_loss(
        labels,
        probabilities,
    )

    loss = log_loss(
        labels,
        probabilities,
    )

    if len(set(labels)) > 1:
        auc = roc_auc_score(
            labels,
            probabilities,
        )

        auc_text = (
            f"{auc:.3f}"
        )

    else:
        auc_text = "N/A"

    print()
    print(treatment)

    print(
        "  Test rows:",
        len(treatment_test),
    )

    print(
        "  ROC-AUC:",
        auc_text,
    )

    print(
        "  Brier:",
        f"{brier:.4f}",
    )

    print(
        "  Log loss:",
        f"{loss:.4f}",
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