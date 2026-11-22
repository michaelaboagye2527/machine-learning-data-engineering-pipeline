# Pipeline plan


## Source

- What: Chicago Food Inspections, Health & Human Services
- Where: https://data.cityofchicago.org/api/v3/views/4ijn-s7e5/query.json
- Format: JSON, one list per field
- Terms: free for non-commercial use
- inspect data using: `curl "https://data.cityofchicago.org/api/v3/views/4ijn-s7e5/query.json"`

## Record key

- One record = Each column in [the dataset](https://data.cityofchicago.org/api/v3/views/4ijn-s7e5/query.json?pageNumber=1&pageSize=10&app_token=$YOUR_APP_TOKEN) is represented by a single `field`
- Key: license_ ` + ` inspection_date ` + ` inspection_type

## Data contract (what "valid" means)



Required fields:



| Column Name       | Data Type          | Description     |
| ----------------- | ------------------ | --------------- |
| `inspection_id`   | number             | Inspection ID   |
| `dba_name`        | text               | DBA Name        |
| `aka_name`        | text               | AKA Name        |
| `license_`        | number             | License #       |
| `facility_type`   | text               | Facility Type   |
| `risk`            | text               | Risk            |
| `address`         | text               | Address         |
| `city`            | text               | City            |
| `state`           | text               | State           |
| `zip`             | number             | Zip             |
| `inspection_date` | floating_timestamp | Inspection Date |
| `inspection_type` | text               | Inspection Type |
| `results`         | text               | Results         |
| `violations`      | text               | Violations      |
| `latitude`        | number             | Latitude        |
| `longitude`       | number             | Longitude       |
| `location`        | location           | Location        |

Rules:

1. `inspection_id` must be a positive number and cannot be null.
2. `inspection_date` must be a valid date and cannot be in the future.
3. `latitude` must be between -90 and 90.
4. `longitude` must be between -180 and 180.
5. No duplicate `inspection_id` records.

## Layers

- Bronze: the JSON response exactly as received, plus where and when we got it
- Silver: one typed row per location and day
- Gold: daily temperature range, 7-day average max temperature, rainy-day flag

## Cadence

- The source adds one day per day and revises recent days for a while
- Run once a day, re-reading the last 3 days each time

## What could go wrong

- API down or slow -> retry
- A field renamed or removed -> reject the batch, keep the Bronze copy
- A missed day -> the next run catches up