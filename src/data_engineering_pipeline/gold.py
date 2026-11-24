

"""Build Gold data for traffic injury prediction using Polars."""

import json
from datetime import datetime, timezone
from pathlib import Path

import polars as pl


SILVER_DIR = Path("data/silver")
GOLD_DIR = Path("data/gold")

INJURY_MAPPING = {
    "FATAL": 1,
    "INCAPACITATING INJURY": 1,
    "NONINCAPACITATING INJURY": 0,
    "REPORTED, NOT EVIDENT": 0,
    "NO INDICATION OF INJURY": 0,
}

# 19 of 29 features by the way
MODEL_FEATURES = [
    "age",
    "person_type",
    "safety_equipment",
    "airbag_deployed",
    "ejection",
    "driver_action",
    "driver_vision",
    "physical_condition",
    "bac_result",
    "bac_result_value",
    "cell_phone_use",
    "pedpedal_action",
    "pedpedal_visibility",
    "pedpedal_location",
    "crash_hour",
    "crash_month",
    "crash_weekday",
    "is_weekend",
    "is_night",
]


def add_gold_features(df: pl.DataFrame) -> pl.DataFrame:
    """Create additional analytical features for the Gold dataset."""

    return df.with_columns(
        # Categorise individuals by age.
        pl.when(pl.col("age").is_null())
        .then(pl.lit(None, dtype=pl.String))
        .when(pl.col("age") < 18)
        .then(pl.lit("UNDER_18"))
        .when(pl.col("age") < 30)
        .then(pl.lit("18_TO_29"))
        .when(pl.col("age") < 60)
        .then(pl.lit("30_TO_59"))
        .otherwise(pl.lit("60_PLUS"))
        .alias("age_group"),

        # Categorise crashes by time of day.
        pl.when(pl.col("crash_hour").is_null())
        .then(pl.lit(None, dtype=pl.String))
        .when(pl.col("crash_hour") < 6)
        .then(pl.lit("OVERNIGHT"))
        .when(pl.col("crash_hour") < 12)
        .then(pl.lit("MORNING"))
        .when(pl.col("crash_hour") < 18)
        .then(pl.lit("AFTERNOON"))
        .otherwise(pl.lit("EVENING"))
        .alias("crash_time_period"),
    )

def find_latest_silver_file(silver_dir: Path = SILVER_DIR) -> Path:

    """Find the most recently modified JSON file under the Silver directory."""

    if not silver_dir.exists():
        raise FileNotFoundError(
            f"Silver directory does not exist: {silver_dir.resolve()}"
        )

    silver_files = list(silver_dir.rglob("*.json"))

    if not silver_files:
        raise FileNotFoundError(
            f"No JSON files found inside: {silver_dir.resolve()}"
        )

    latest_file = max(silver_files, key=lambda file: file.stat().st_mtime)

    print(f"Silver file selected: {latest_file.resolve()}")
    return latest_file


def load_silver_data(silver_file: Path) -> pl.DataFrame:
    
    """Load records from the exact Silver JSON file."""

    with silver_file.open("r", encoding="utf-8") as file:
        records = json.load(file)

    # Support either a list of records or a dictionary containing "data".
    if isinstance(records, dict):
        records = records.get("data", [])

    if not records:
        raise ValueError(f"No records found in {silver_file}")

    return pl.DataFrame(records, infer_schema_length=None)


def build_gold(
    silver_file: str | Path | None = None,
    gold_dir: str | Path = GOLD_DIR,
) -> Path:
    """Transform Silver records into a Gold Parquet dataset."""

    # Locate the Silver file automatically unless one is supplied.
    if silver_file is None:
        silver_path = find_latest_silver_file()
    else:
        silver_path = Path(silver_file)

        if not silver_path.is_file():
            raise FileNotFoundError(
                f"Silver file not found: {silver_path.resolve()}"
            )

    df = load_silver_data(silver_path)

    required_columns = [
        "person_id",
        "injury_classification",
        "crash_record_id",
        "crash_date",
    ]

    missing_required = [
        column for column in required_columns if column not in df.columns
    ]

    if missing_required:
        raise ValueError(
            f"Silver data is missing required columns: {missing_required}"
        )

    # Create optional columns if they are absent from the Silver data.
    optional_columns = set(MODEL_FEATURES + ["sex"])

    missing_optional = optional_columns.difference(df.columns)

    if missing_optional:
        df = df.with_columns(
            [pl.lit(None).alias(column) for column in missing_optional]
        )

    # Standardise the injury classification before mapping the target.
    df = df.with_columns(
        pl.col("injury_classification")
        .cast(pl.String)
        .str.to_uppercase()
        .str.strip_chars()
        .alias("injury_classification")
    )

    # Create the binary target.
    df = df.with_columns(
        pl.when(
            pl.col("injury_classification").is_in(
                ["FATAL", "INCAPACITATING INJURY"]
            )
        )
        .then(1)
        .when(
            pl.col("injury_classification").is_in(
                [
                    "NONINCAPACITATING INJURY",
                    "REPORTED, NOT EVIDENT",
                    "NO INDICATION OF INJURY",
                ]
            )
        )
        .then(0)
        .otherwise(None)
        .cast(pl.Int8)
        .alias("serious_injury")
    )

    # Exclude records without a recognised target or crash identifier.
    df = df.filter(
        pl.col("serious_injury").is_not_null()
        & pl.col("crash_record_id").is_not_null()
    )

    if df.is_empty():
        raise ValueError(
            "No usable records remain after target and identifier filtering. "
            "Check the injury classification values in the Silver data."
        )

    # Convert numeric fields safely.
    df = df.with_columns(
        pl.col("age").cast(pl.Float64, strict=False),
        pl.col("bac_result_value").cast(pl.Float64, strict=False),
    )

    # Treat invalid numeric values as missing.
    df = df.with_columns(
        pl.when(pl.col("age").is_between(0, 120))
        .then(pl.col("age"))
        .otherwise(None)
        .alias("age"),

        pl.when(pl.col("bac_result_value") >= 0)
        .then(pl.col("bac_result_value"))
        .otherwise(None)
        .alias("bac_result_value"),
    )

    # Standardise categorical fields.
    categorical_columns = [
        "person_type",
        "safety_equipment",
        "airbag_deployed",
        "ejection",
        "driver_action",
        "driver_vision",
        "physical_condition",
        "bac_result",
        "cell_phone_use",
        "pedpedal_action",
        "pedpedal_visibility",
        "pedpedal_location",
    ]

    df = df.with_columns(
        [
            pl.col(column)
            .cast(pl.String)
            .str.to_uppercase()
            .str.strip_chars()
            .alias(column)
            for column in categorical_columns
        ]
    )

    # Parse crash_date and derive time-related features.
    df = df.with_columns(
        pl.col("crash_date")
        .cast(pl.String)
        .str.to_datetime(strict=False)
        .alias("_crash_datetime")
    )

    df = df.with_columns(
        pl.col("_crash_datetime").dt.hour().alias("crash_hour"),
        pl.col("_crash_datetime").dt.month().alias("crash_month"),
        pl.col("_crash_datetime").dt.weekday().alias("crash_weekday"),
        (pl.col("_crash_datetime").dt.weekday() >= 6).alias("is_weekend"),
        (
            (pl.col("_crash_datetime").dt.hour() >= 20)
            | (pl.col("_crash_datetime").dt.hour() < 6)
        ).alias("is_night"),
    )

    # Keep model features, target, and metadata for evaluation.
    gold_df = df.select(
    [
        "person_id",
        *MODEL_FEATURES,
        "serious_injury",
        "crash_record_id",
        "sex",
    ]
).rename({"sex": "audit_sex"})

    # Save Gold data in a date-partitioned Parquet directory.
    processing_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    output_dir = Path(gold_dir) / f"ingest_date={processing_date}"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "traffic_injury_prediction.parquet"

    gold_df.write_parquet(output_file)

    print("\nGold data successfully created.")
    print(f"Source Silver file: {silver_path.resolve()}")
    print(f"Gold file: {output_file.resolve()}")
    print(f"Total Gold records: {gold_df.height}")
    print(f"Serious injuries: {gold_df['serious_injury'].sum()}")
    print(
        f"Non-serious injuries: "
        f"{gold_df.filter(pl.col('serious_injury') == 0).height}"
    )

    return output_file


if __name__ == "__main__":
    build_gold()












