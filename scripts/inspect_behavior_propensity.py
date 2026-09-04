"""
Inspect historical treatment propensities.

This does not train a model.
It only helps us understand how biased the historical
action-assignment policy is and how large IPW weights would become.
"""

import pandas as pd


DATA_PATH = "data/historical_recovery.csv"


data = pd.read_csv(
    DATA_PATH
)


print()
print("BEHAVIOR PROPENSITY INSPECTION")
print("==============================")

print()
print("Rows:", len(data))


propensity = data[
    "behavior_policy_probability"
]


print()
print("OVERALL PROPENSITY")
print("------------------")

print(
    "Minimum:",
    round(
        propensity.min(),
        4,
    ),
)

print(
    "Mean:",
    round(
        propensity.mean(),
        4,
    ),
)

print(
    "Maximum:",
    round(
        propensity.max(),
        4,
    ),
)


print()
print("PROPENSITY QUANTILES")
print("--------------------")

for quantile in [
    0.01,
    0.05,
    0.10,
    0.25,
    0.50,
    0.75,
    0.90,
    0.95,
    0.99,
]:

    value = propensity.quantile(
        quantile
    )

    print(
        f"{quantile:>5.0%}:",
        round(
            value,
            4,
        ),
    )


data[
    "ipw_weight"
] = (
    1.0
    /
    data[
        "behavior_policy_probability"
    ]
)


print()
print("IPW WEIGHT SUMMARY")
print("------------------")

print(
    "Minimum:",
    round(
        data[
            "ipw_weight"
        ].min(),
        2,
    ),
)

print(
    "Mean:",
    round(
        data[
            "ipw_weight"
        ].mean(),
        2,
    ),
)

print(
    "Maximum:",
    round(
        data[
            "ipw_weight"
        ].max(),
        2,
    ),
)


print()
print("BY TREATMENT")
print("------------")

summary = (
    data
    .groupby(
        "treatment"
    )
    .agg(
        rows=(
            "treatment",
            "size",
        ),

        mean_propensity=(
            "behavior_policy_probability",
            "mean",
        ),

        min_propensity=(
            "behavior_policy_probability",
            "min",
        ),

        max_propensity=(
            "behavior_policy_probability",
            "max",
        ),

        mean_ipw=(
            "ipw_weight",
            "mean",
        ),

        max_ipw=(
            "ipw_weight",
            "max",
        ),
    )
    .sort_index()
)


print(
    summary.to_string(
        float_format=lambda value:
            f"{value:.3f}"
    )
)


print()
print("LOW-PROPENSITY ROW COUNTS")
print("-------------------------")

for threshold in [
    0.20,
    0.10,
    0.05,
    0.02,
]:

    count = int(
        (
            propensity
            < threshold
        ).sum()
    )

    percentage = (
        count
        / len(data)
        * 100
    )

    print(
        f"< {threshold:.2f}:",
        count,
        f"({percentage:.2f}%)",
    )