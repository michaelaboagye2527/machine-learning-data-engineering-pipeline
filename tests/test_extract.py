
import json

import pytest

from data_engineering_pipeline import extract
from data_engineering_pipeline.extract import (
    TemporarySourceError,
    fetch_traffic_crash,
    save_bronze,
)


def test_bronze_keeps_payload(monkeypatch, tmp_path):
    """Check that the original API payload is preserved in Bronze."""

    payload = [
        {
            "person_id": "O2421380",
            "person_type": "DRIVER",
            "age": "29",
        }
    ]

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return payload

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(extract.httpx, "get", fake_get)

    result = fetch_traffic_crash()

    file_path = save_bronze(
        payload=result,
        source="chicago_traffic_crashes",
        bronze_dir=str(tmp_path),
    )

    with file_path.open(encoding="utf-8") as file:
        saved_data = json.load(file)

    assert saved_data["data"] == payload
    assert saved_data["_source"] == "chicago_traffic_crashes"
    assert "_ingested_at" in saved_data


def test_503_raises_temporary_source_error(monkeypatch):
    """Check that server errors are treated as temporary failures."""

    class FakeResponse:
        status_code = 503

    def fake_get(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(extract.httpx, "get", fake_get)

    with pytest.raises(TemporarySourceError):
        fetch_traffic_crash()
