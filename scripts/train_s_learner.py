from pathlib import Path

import joblib
import pandas as pd

from sklearn.metrics import (
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit

from ml.s_learner import PooledSLearner
import argparse
from ml.features import (
    METHOD_HISTORY_NUMERIC_FEATURES,
)

parser = argparse.ArgumentParser()

feature_group = (
    parser.add_mutually_exclusive_group()
)

feature_group.add_argument(
    "--method-history",
    action="store_true",
)

feature_group.add_argument(
    "--candidate-method-history",
    action="store_true",
)

args = parser.parse_args()

DATA_PATH = Path(
    "data/historical_recovery.csv"
)

if args.method_history:
    MODEL_PATH = Path(
        "models/s_learner_method_history.joblib"
    )

elif args.candidate_method_history:
    MODEL_PATH = Path(
        "models/s_learner_candidate_method_history.joblib"
    )

else:
    MODEL_PATH = Path(
        "models/s_learner_corrected_baseline.joblib"
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



if args.method_history:
    learner = PooledSLearner(
        extra_numeric_features=(
            METHOD_HISTORY_NUMERIC_FEATURES
        )
    )

    model_name = (
        "S-LEARNER + METHOD HISTORY"
    )


elif args.candidate_method_history:
    learner = PooledSLearner(
        use_candidate_method_history=True
    )

    model_name = (
        "S-LEARNER + CANDIDATE METHOD HISTORY"
    )


else:
    learner = PooledSLearner()

    model_name = (
        "S-LEARNER CORRECTED BASELINE"
    )


print()
print(model_name)
print("-------------------------")

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