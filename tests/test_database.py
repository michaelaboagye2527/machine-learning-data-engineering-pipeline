
import polars as pl

from data_engineering_pipeline.database import save_to_database


def test_loading_same_batch_twice_is_idempotent(tmp_path):
    db_path = tmp_path / "test.sqlite3"

    silver_df = pl.DataFrame({
        "person_id": ["P001", "P002"],
        "person_type": ["Driver", "Passenger"],
    })

    gold_df = pl.DataFrame({
        "person_id": ["P001"],
        "serious_injury": [1],
        "age_group": ["30_TO_59"],
    })

    # Load the same data twice.
    save_to_database(silver_df, gold_df, db_path=db_path)
    save_to_database(silver_df, gold_df, db_path=db_path)

    import sqlite3

    with sqlite3.connect(db_path) as conn:
        silver_count = conn.execute(
            "SELECT COUNT(*) FROM silver_traffic_people"
        ).fetchone()[0]

        gold_count = conn.execute(
            "SELECT COUNT(*) FROM gold_traffic_injury"
        ).fetchone()[0]

    assert silver_count == 2
    assert gold_count == 1
