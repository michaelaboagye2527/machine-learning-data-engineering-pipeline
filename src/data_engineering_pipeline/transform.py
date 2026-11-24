
"""Validate Bronze data and produce clean Silver data."""

import json
from datetime import datetime, timezone
from pathlib import Path


def validate_record(record: dict) -> list:
    """Return a list of validation errors for one record."""

    errors = []

    # Required fields
    for column in ["person_id", "crash_record_id"]:
        value = record.get(column)

        if value is None or str(value).strip() == "":
            errors.append(f"{column} cannot be empty")

    # Validate age when provided
    age = record.get("age")

    if age not in (None, ""):
        try:
            age_value = float(age)

            if not 0 <= age_value <= 120:
                errors.append("age must be between 0 and 120")

        except (ValueError, TypeError):
            errors.append("age must be numeric")

    # Validate BAC result when provided
    bac = record.get("bac_result_value")

    if bac not in (None, ""):
        try:
            bac_value = float(bac)

            if bac_value < 0:
                errors.append("bac_result_value cannot be negative")

        except (ValueError, TypeError):
            errors.append("bac_result_value must be numeric")

    # Validate crash date
    crash_date = record.get("crash_date")

    if not crash_date:
        errors.append("crash_date cannot be empty")
    else:
        try:
            parsed_date = datetime.fromisoformat(
                str(crash_date).replace("Z", "+00:00")
            )

            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=timezone.utc)

            if parsed_date > datetime.now(timezone.utc):
                errors.append("crash_date cannot be in the future")

        except ValueError:
            errors.append("crash_date must be a valid timestamp")

    return errors


def transform_record(record: dict) -> dict:
    """Clean and standardize a valid record."""

    cleaned = record.copy()

    # Standardize text fields
    for column, value in cleaned.items():
        if isinstance(value, str):
            cleaned[column] = value.strip()

    # Convert numeric fields
    if cleaned.get("age") not in (None, ""):
        age = float(cleaned["age"])
        cleaned["age"] = int(age) if age.is_integer() else age

    if cleaned.get("bac_result_value") not in (None, ""):
        cleaned["bac_result_value"] = float(
            cleaned["bac_result_value"]
        )

    return cleaned


def transform_bronze_file(
    bronze_file: str,
    silver_dir: str = "data/silver",
    quarantine_dir: str = "data/quarantine",
) -> tuple[Path, Path | None]:
    """Read Bronze data, validate it and save Silver output."""

    with open(bronze_file, encoding="utf-8") as file:
        bronze_data = json.load(file)

    records = bronze_data["data"]

    valid_records = []
    rejected_records = []

    for record in records:
        errors = validate_record(record)

        if errors:
            rejected_records.append({
                "record": record,
                "errors": errors
            })
        else:
            valid_records.append(transform_record(record))

    # Create Silver output directory
    date_folder = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_dir = Path(silver_dir) / f"ingest_date={date_folder}"
    output_dir.mkdir(parents=True, exist_ok=True)

    silver_file = output_dir / f"{Path(bronze_file).stem}.json"

    with silver_file.open("w", encoding="utf-8") as file:
        json.dump(valid_records, file, indent=4, ensure_ascii=False)

    # Keep rejected records separately for investigation
    quarantine_file = None

    if rejected_records:
        quarantine_output = (
            Path(quarantine_dir) / f"ingest_date={date_folder}"
        )
        quarantine_output.mkdir(parents=True, exist_ok=True)

        quarantine_file = (
            quarantine_output / f"{Path(bronze_file).stem}.json"
        )

        with quarantine_file.open("w", encoding="utf-8") as file:
            json.dump(rejected_records, file, indent=4, ensure_ascii=False)

    print(f"Total records: {len(records)}")
    print(f"Valid records: {len(valid_records)}")
    print(f"Rejected records: {len(rejected_records)}")
    print(f"Silver file: {silver_file}")

    return silver_file, quarantine_file
