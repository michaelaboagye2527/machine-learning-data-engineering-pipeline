
"""Store Silver and Gold datasets in SQLite using upserts."""

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

import polars as pl

from data_engineering_pipeline.gold import (
    find_latest_silver_file,
    load_silver_data,
)


DATABASE_PATH = Path("data/pipeline.sqlite3")
SILVER_TABLE = "silver_traffic_people"
GOLD_TABLE = "gold_traffic_injury"


def quote_identifier(name: str) -> str:
    """Safely quote an SQLite identifier."""
    return '"' + name.replace('"', '""') + '"'


def sqlite_type(dtype) -> str:
    """Convert a Polars data type to an SQLite storage type."""

    name = str(dtype)

    if name.startswith(("Int", "UInt", "Boolean")):
        return "INTEGER"

    if name.startswith(("Float", "Decimal")):
        return "REAL"

    return "TEXT"


def validate_primary_key(df: pl.DataFrame) -> None:
    """Ensure person_id is present, non-null and unique."""

    if "person_id" not in df.columns:
        raise ValueError("The DataFrame must contain person_id.")

    df = df.with_columns(
        pl.col("person_id").cast(pl.String)
    )

    if df["person_id"].null_count() > 0:
        raise ValueError("person_id contains null values.")

    if df.filter(pl.col("person_id").str.strip_chars() == "").height:
        raise ValueError("person_id contains empty values.")

    if df["person_id"].n_unique() != df.height:
        raise ValueError("Duplicate person_id values detected.")


def ensure_table(
    connection: sqlite3.Connection,
    table_name: str,
    df: pl.DataFrame,
) -> None:
    """Create a table and add any missing DataFrame columns."""

    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {quote_identifier(table_name)} (
            "person_id" TEXT PRIMARY KEY
        )
        """
    )

    existing_columns = {
        row[1]
        for row in connection.execute(
            f"PRAGMA table_info({quote_identifier(table_name)})")
    }

    for column, dtype in df.schema.items():
        if column not in existing_columns:
            sql_type = sqlite_type(dtype)

            connection.execute(
                f"""
                ALTER TABLE {quote_identifier(table_name)}
                ADD COLUMN {quote_identifier(column)} {sql_type}
                """
            )


def convert_value(value):
    """Convert Python values into SQLite-compatible values."""

    if isinstance(value, bool):
        return int(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, (dict, list)):
        return json.dumps(value)

    return value


def upsert_dataframe(
    connection: sqlite3.Connection,
    table_name: str,
    df: pl.DataFrame,
) -> None:
    """Insert new records or update existing records."""

    validate_primary_key(df)

    ensure_table(connection, table_name, df)

    columns = df.columns

    column_names = ", ".join(
        quote_identifier(column) for column in columns
    )

    placeholders = ", ".join("?" for _ in columns)

    update_columns = [
        column for column in columns if column != "person_id"
    ]

    update_statement = ", ".join(
        f"{quote_identifier(column)} = excluded.{quote_identifier(column)}"
        for column in update_columns
    )

    sql = f"""
        INSERT INTO {quote_identifier(table_name)} ({column_names})
        VALUES ({placeholders})
        ON CONFLICT("person_id") DO UPDATE SET
        {update_statement}
    """

    rows = [
        tuple(convert_value(value) for value in row)
        for row in df.iter_rows()
    ]

    connection.executemany(sql, rows)

    print(f"Upserted {len(rows)} records into {table_name}.")


def find_latest_gold_file(gold_dir: Path = Path("data/gold")) -> Path:
    """Find the most recently modified Gold Parquet file."""

    if not gold_dir.exists():
        raise FileNotFoundError(
            f"Gold directory does not exist: {gold_dir.resolve()}"
        )

    files = list(gold_dir.rglob("*.parquet"))

    if not files:
        raise FileNotFoundError(
            f"No Gold Parquet files found inside {gold_dir.resolve()}"
        )

    return max(files, key=lambda file: file.stat().st_mtime)



def save_to_database(
    silver_df: pl.DataFrame,
    gold_df: pl.DataFrame,
) -> None:
    """Save both datasets atomically in one SQLite transaction."""

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    silver_df = silver_df.with_columns(
        pl.col("person_id").cast(pl.String)
    )

    gold_df = gold_df.with_columns(
        pl.col("person_id").cast(pl.String)
    )

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        connection.execute("BEGIN")

        # Load Silver data
        upsert_dataframe(
            connection,
            SILVER_TABLE,
            silver_df,
        )

        # Deliberately simulate a failure
       # raise RuntimeError("boom")

        # Load Gold data
        upsert_dataframe(
            connection,
            GOLD_TABLE,
            gold_df,
        )

        connection.commit()
        print("Both datasets saved successfully.")

    except Exception:
        connection.rollback()
        print("Database transaction failed. Changes rolled back.")
        raise

    finally:
        connection.close()



def load_latest_batches() -> None:
    """Locate the latest Silver and Gold files and save them."""

    silver_file = find_latest_silver_file()
    gold_file = find_latest_gold_file()

    print(f"Silver source: {silver_file.resolve()}")
    print(f"Gold source: {gold_file.resolve()}")

    silver_df = load_silver_data(silver_file)
    gold_df = pl.read_parquet(gold_file)

    print(f"Silver records: {silver_df.height}")
    print(f"Gold records: {gold_df.height}")

    save_to_database(silver_df, gold_df)


if __name__ == "__main__":
    load_latest_batches()
