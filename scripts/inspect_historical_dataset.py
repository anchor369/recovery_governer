import csv
from collections import Counter, defaultdict
from pathlib import Path


DATA_PATH = Path(
    "data/historical_recovery.csv"
)


with DATA_PATH.open(
    encoding="utf-8",
) as csv_file:

    rows = list(
        csv.DictReader(csv_file)
    )


action_counts = Counter()

recovery_counts = defaultdict(
    lambda: {
        "total": 0,
        "recovered": 0,
    }
)

behavior_probabilities = []

failure_counts = Counter()


for row in rows:

    treatment = row["treatment"]

    recovered = int(
        row["recovered"]
    )

    action_counts[
        treatment
    ] += 1

    recovery_counts[
        treatment
    ][
        "total"
    ] += 1

    recovery_counts[
        treatment
    ][
        "recovered"
    ] += recovered

    behavior_probabilities.append(
        float(
            row[
                "behavior_policy_probability"
            ]
        )
    )

    failure_counts[
        row["failure_category"]
    ] += 1


def percent(
    numerator,
    denominator,
):

    if denominator == 0:
        return 0.0

    return (
        numerator
        / denominator
        * 100.0
    )


print()
print("HISTORICAL DATASET SUMMARY")
print("--------------------------")

print(
    "Rows:",
    len(rows),
)


print()
print("TREATMENT DISTRIBUTION")
print("----------------------")

for treatment, count in (
    action_counts.most_common()
):

    print(
        f"{treatment:24}",
        count,
        f"({percent(count, len(rows)):.2f}%)",
    )


print()
print("OBSERVED RECOVERY BY TREATMENT")
print("------------------------------")

for treatment in sorted(
    recovery_counts
):

    values = recovery_counts[
        treatment
    ]

    rate = percent(
        values["recovered"],
        values["total"],
    )

    print(
        f"{treatment:24}",
        f"{rate:.2f}%",
        f"n={values['total']}",
    )


print()
print("FAILURE DISTRIBUTION")
print("--------------------")

for failure, count in (
    failure_counts.most_common()
):

    print(
        f"{failure:32}",
        count,
        f"({percent(count, len(rows)):.2f}%)",
    )


print()
print("BEHAVIOR POLICY PROBABILITY")
print("---------------------------")

print(
    "Minimum:",
    f"{min(behavior_probabilities):.4f}",
)

print(
    "Mean:",
    f"{sum(behavior_probabilities) / len(behavior_probabilities):.4f}",
)

print(
    "Maximum:",
    f"{max(behavior_probabilities):.4f}",
)