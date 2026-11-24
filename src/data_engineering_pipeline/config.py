
"""Central configuration for the Chicago traffic crashes data pipeline."""

import os

from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE = os.getenv("DATABASE_URL") or "data/pipeline.sqlite3"

# Raw data storage (Bronze layer)
BRONZE_DIR = os.getenv("BRONZE_DIR") or "data/bronze"

# Chicago Data Portal API configuration
API_URL = "https://data.cityofchicago.org/resource/u6pd-qa9d.json"
CHICAGO_APP_TOKEN = os.getenv("CHICAGO_APP_TOKEN")

# Data ingestion settings
FIRST_LOAD_DAYS = 30
OVERLAP_DAYS = 3

# Data validation rules
REQUIRED_COLUMNS = [
    "person_id",
    "person_type",
    "crash_record_id",
    "crash_date",
]

UNIQUE_COLUMNS = ["person_id"]

NUMERIC_COLUMNS = [
    "age",
    "bac_result_value",
]

TIMESTAMP_COLUMNS = [
    "crash_date",
]

# Expected dataset schema
SCHEMA = {
    "person_id": "text",
    "person_type": "text",
    "crash_record_id": "text",
    "vehicle_id": "text",
    "crash_date": "floating_timestamp",
    "seat_no": "text",
    "city": "text",
    "state": "text",
    "zipcode": "text",
    "sex": "text",
    "age": "number",
    "drivers_license_state": "text",
    "drivers_license_class": "text",
    "safety_equipment": "text",
    "airbag_deployed": "text",
    "ejection": "text",
    "injury_classification": "text",
    "hospital": "text",
    "ems_agency": "text",
    "ems_run_no": "text",
    "driver_action": "text",
    "driver_vision": "text",
    "physical_condition": "text",
    "pedpedal_action": "text",
    "pedpedal_visibility": "text",
    "pedpedal_location": "text",
    "bac_result": "text",
    "bac_result_value": "number",
    "cell_phone_use": "text",
}
