import csv
from datetime import datetime, timezone
from pathlib import Path

from simulator.config import SimulatorConfig
from simulator.historical_dataset import (
    HistoricalDatasetGenerator,
)
from simulator.random_source import RandomSource


REFERENCE_TIME = datetime(
    2026,
    9,
    4,
    tzinfo=timezone.utc,
)

TARGET_ROWS = 20000

OUTPUT_PATH = Path(
    "data/historical_recovery.csv"
)


config = SimulatorConfig()

random_source = RandomSource(
    config.random_seed
)

generator = HistoricalDatasetGenerator(
    config=config,
    random_source=random_source,
    reference_time=REFERENCE_TIME,
)


print(
    f"Generating {TARGET_ROWS} historical recovery decisions..."
)

rows = generator.generate_rows(
    target_rows=TARGET_ROWS
)

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

with OUTPUT_PATH.open(
    "w",
    newline="",
    encoding="utf-8",
) as csv_file:

    writer = csv.DictWriter(
        csv_file,
        fieldnames=rows[0].keys(),
    )

    writer.writeheader()
    writer.writerows(rows)


print()
print(
    "Saved:",
    OUTPUT_PATH,
)

print(
    "Rows:",
    len(rows),
)

print(
    "Columns:",
    len(rows[0]),
)