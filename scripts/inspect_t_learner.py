from pathlib import Path

import joblib
import pandas as pd


DATA_PATH = Path(
    "data/historical_recovery.csv"
)

MODEL_PATH = Path(
    "models/t_learner.joblib"
)


data = pd.read_csv(
    DATA_PATH
)

learner = joblib.load(
    MODEL_PATH
)


sample = (
    data.sample(
        n=10,
        random_state=42,
    )
    .copy()
)


predictions = (
    learner.predict_all_treatments(
        sample
    )
)


print()
print("COUNTERFACTUAL MODEL PREDICTIONS")
print("--------------------------------")


for row_position in range(
    len(sample)
):

    row = sample.iloc[
        row_position
    ]

    print()
    print(
        "Decision:",
        row["decision_id"],
    )

    print(
        "Failure:",
        row["failure_category"],
    )

    print(
        "Method:",
        row["current_method"],
    )

    print(
        "Historical action:",
        row["treatment"],
    )

    print(
        "Historical outcome:",
        row["recovered"],
    )

    no_action_probability = (
        predictions[
            "NO_ACTION"
        ][
            row_position
        ]
    )

    print(
        "  NO_ACTION:",
        f"{no_action_probability:.3f}",
    )

    for treatment in sorted(
        predictions
    ):

        if treatment == "NO_ACTION":
            continue

        probability = (
            predictions[
                treatment
            ][
                row_position
            ]
        )

        uplift = (
            probability
            - no_action_probability
        )

        print(
            f"  {treatment:22}",
            f"P={probability:.3f}",
            f"uplift={uplift:+.3f}",
        )