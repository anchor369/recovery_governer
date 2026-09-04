"""
Inspect doubly-robust pseudo-outcomes on real historical rows.

This script does not train the final DR learner.
It uses cross-fitted S-learner predictions so we can inspect
how observed outcomes and propensities create DR corrections.
"""

import pandas as pd

from ml.crossfit import (
    generate_cross_fitted_predictions,
)
from ml.dr import (
    calculate_dr_pseudo_outcome,
)


DATA_PATH = "data/historical_recovery.csv"

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
print("DR PSEUDO-OUTCOME INSPECTION")
print("============================")

print()
print(
    "Rows:",
    len(data),
)

print(
    "Treatments:",
    treatments,
)


# ---------------------------------------------------------
# CROSS-FITTED FIRST-STAGE PREDICTIONS
# ---------------------------------------------------------

print()
print("GENERATING CROSS-FITTED S-LEARNER PREDICTIONS")
print("---------------------------------------------")

cross_fitted_predictions = (
    generate_cross_fitted_predictions(
        dataframe=data,
        treatments=treatments,
        n_splits=N_SPLITS,
    )
)


# ---------------------------------------------------------
# BUILD DR INFORMATION FOR EACH OBSERVED ROW
# ---------------------------------------------------------

inspection_rows = []


for row_position, (_, row) in enumerate(
    data.iterrows()
):

    observed_treatment = row[
        "treatment"
    ]

    observed_outcome = int(
        row[
            "recovered"
        ]
    )

    propensity = float(
        row[
            "behavior_policy_probability"
        ]
    )

    predicted_probability = float(
        cross_fitted_predictions[
            observed_treatment
        ][
            row_position
        ]
    )

    residual = (
        observed_outcome
        - predicted_probability
    )

    correction = (
        residual
        / propensity
    )

    dr_pseudo_outcome = (
        calculate_dr_pseudo_outcome(
            predicted_probability=(
                predicted_probability
            ),
            observed_outcome=(
                observed_outcome
            ),
            action_was_observed=True,
            behavior_propensity=(
                propensity
            ),
        )
    )

    inspection_rows.append(
        {
            "row_position":
                row_position,

            "customer_id":
                row[
                    "customer_id"
                ],

            "treatment":
                observed_treatment,

            "recovered":
                observed_outcome,

            "propensity":
                propensity,

            "s_prediction":
                predicted_probability,

            "residual":
                residual,

            "dr_correction":
                correction,

            "dr_pseudo_outcome":
                dr_pseudo_outcome,
        }
    )


inspection = pd.DataFrame(
    inspection_rows
)


# ---------------------------------------------------------
# SELECT EXAMPLES WITH DIFFERENT PROPENSITIES
# ---------------------------------------------------------

low_propensity_examples = (
    inspection
    .sort_values(
        "propensity",
        ascending=True,
    )
    .head(3)
)


high_propensity_examples = (
    inspection
    .sort_values(
        "propensity",
        ascending=False,
    )
    .head(3)
)


middle_index = (
    inspection[
        "propensity"
    ]
    .sub(
        inspection[
            "propensity"
        ].median()
    )
    .abs()
    .idxmin()
)


middle_example = (
    inspection.loc[
        [
            middle_index
        ]
    ]
)


examples = pd.concat(
    [
        low_propensity_examples,
        middle_example,
        high_propensity_examples,
    ],
    ignore_index=True,
)


# ---------------------------------------------------------
# PRINT EXAMPLES
# ---------------------------------------------------------

print()
print("REAL DR EXAMPLES")
print("================")


for example_number, row in (
    examples.iterrows()
):

    print()

    print(
        f"Example {example_number + 1}"
    )

    print(
        "-" * 30
    )

    print(
        "Treatment:",
        row[
            "treatment"
        ],
    )

    print(
        "Actual recovered:",
        int(
            row[
                "recovered"
            ]
        ),
    )

    print(
        "Behavior propensity:",
        f"{row['propensity']:.4f}",
    )

    print(
        "Cross-fitted S prediction:",
        f"{row['s_prediction']:.4f}",
    )

    print(
        "Prediction residual:",
        f"{row['residual']:+.4f}",
    )

    print(
        "DR correction:",
        f"{row['dr_correction']:+.4f}",
    )

    print(
        "DR pseudo-outcome:",
        f"{row['dr_pseudo_outcome']:+.4f}",
    )


print()
print("SUMMARY")
print("=======")

print(
    "Mean absolute residual:",
    f"{inspection['residual'].abs().mean():.4f}",
)

print(
    "Mean absolute DR correction:",
    f"{inspection['dr_correction'].abs().mean():.4f}",
)

print(
    "Minimum DR pseudo-outcome:",
    f"{inspection['dr_pseudo_outcome'].min():.4f}",
)

print(
    "Maximum DR pseudo-outcome:",
    f"{inspection['dr_pseudo_outcome'].max():.4f}",
)

print(
    "Pseudo-outcomes below 0:",
    int(
        (
            inspection[
                "dr_pseudo_outcome"
            ]
            < 0
        ).sum()
    ),
)

print(
    "Pseudo-outcomes above 1:",
    int(
        (
            inspection[
                "dr_pseudo_outcome"
            ]
            > 1
        ).sum()
    ),
)