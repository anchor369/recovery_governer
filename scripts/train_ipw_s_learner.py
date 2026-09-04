from pathlib import Path

import joblib
import pandas as pd

from sklearn.metrics import (
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit

from ml.ipw_s_learner import IPWPooledSLearner

DATA_PATH = Path(
    "data/historical_recovery.csv"
)

MODEL_PATH = Path(
    "models/ipw_s_learner.joblib"
)


data = pd.read_csv(
    DATA_PATH
)


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
print("POOLED IPW S-LEARNER TRAINING")
print("-------------------------")

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
    train_data["customer_id"].nunique(),
)

print(
    "Test customers:",
    test_data["customer_id"].nunique(),
)


learner = IPWPooledSLearner()

learner.fit(
    train_data
)


print()
print("OVERALL FACTUAL PERFORMANCE")
print("---------------------------")


probabilities = learner.predict_probability(
    test_data
)

labels = test_data[
    "recovered"
].to_numpy()


auc = roc_auc_score(
    labels,
    probabilities,
)

brier = brier_score_loss(
    labels,
    probabilities,
)

loss = log_loss(
    labels,
    probabilities,
)


print(
    "ROC-AUC:",
    f"{auc:.3f}",
)

print(
    "Brier:",
    f"{brier:.4f}",
)

print(
    "Log loss:",
    f"{loss:.4f}",
)


print()
print("FACTUAL PERFORMANCE BY TREATMENT")
print("--------------------------------")


for treatment in sorted(
    test_data["treatment"].unique()
):

    treatment_data = test_data[
        test_data["treatment"]
        == treatment
    ]

    treatment_probabilities = (
        learner.predict_probability(
            treatment_data
        )
    )

    treatment_labels = (
        treatment_data["recovered"]
        .to_numpy()
    )

    treatment_brier = (
        brier_score_loss(
            treatment_labels,
            treatment_probabilities,
        )
    )

    treatment_loss = (
        log_loss(
            treatment_labels,
            treatment_probabilities,
        )
    )

    if len(set(treatment_labels)) > 1:

        treatment_auc = (
            roc_auc_score(
                treatment_labels,
                treatment_probabilities,
            )
        )

        auc_text = (
            f"{treatment_auc:.3f}"
        )

    else:
        auc_text = "N/A"

    print()
    print(treatment)

    print(
        "  Test rows:",
        len(treatment_data),
    )

    print(
        "  ROC-AUC:",
        auc_text,
    )

    print(
        "  Brier:",
        f"{treatment_brier:.4f}",
    )

    print(
        "  Log loss:",
        f"{treatment_loss:.4f}",
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