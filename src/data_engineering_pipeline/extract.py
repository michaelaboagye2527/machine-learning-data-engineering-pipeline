
"""Extract Chicago traffic crash data and save it to Bronze storage."""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://data.cityofchicago.org/resource/u6pd-qa9d.json"
APP_TOKEN = os.getenv("CHICAGO_APP_TOKEN")


class TemporarySourceError(Exception):
    """Raised when the API experiences a temporary failure."""


def fetch_traffic_crash(
    limit: int = 1000,
) -> list:
    """Fetch real traffic crash records from the Chicago API."""

    headers = {}

    if APP_TOKEN:
        headers["X-App-Token"] = APP_TOKEN

    params = {
        "$limit": limit
    }

    try:
        response = httpx.get(
            API_URL,
            params=params,
            headers=headers,
            timeout=30.0,
        )

        if response.status_code == 429 or 500 <= response.status_code < 600:
            raise TemporarySourceError(
                f"Temporary API error: HTTP {response.status_code}"
            )

        response.raise_for_status()

        return response.json()

    except httpx.TimeoutException as exc:
        raise TemporarySourceError("API request timed out") from exc

    except httpx.TransportError as exc:
        raise TemporarySourceError("API connection failed") from exc


def save_bronze(
    payload: list,
    source: str = API_URL,
    bronze_dir: str = "data/bronze",
) -> Path:
    """Save the original API response with ingestion metadata."""

    ingested_at = datetime.now(timezone.utc)

    output_dir = (
        Path(bronze_dir)
        / f"ingest_date={ingested_at.strftime('%Y-%m-%d')}"
    )

    output_dir.mkdir(parents=True, exist_ok=True)

    record = {
        "_source": source,
        "_ingested_at": ingested_at.isoformat(),
        "data": payload,
    }

    file_path = output_dir / f"{uuid.uuid4()}.json"

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(record, file, indent=4, ensure_ascii=False)

    return file_path


def extract_and_save() -> Path:
    """Fetch real API data and save it to Bronze storage."""

    payload = fetch_traffic_crash(limit=1000)

    file_path = save_bronze(payload)

    print(f"Retrieved {len(payload)} records from the API.")
    print(f"Bronze file saved at: {file_path}")

    return file_path
