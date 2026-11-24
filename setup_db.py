
import sqlite3
from pathlib import Path

from data_engineering_pipeline.config import DATABASE


def create_database():
    """Create the SQLite database if it doesn't exist."""

    Path(DATABASE).parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE) as conn:
        print(f"Database ready: {DATABASE}")


if __name__ == "__main__":
    create_database()