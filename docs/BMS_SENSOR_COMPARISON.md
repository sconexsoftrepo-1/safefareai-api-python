# BMS vs Sensor passenger comparison

For each of the five BMS stops, compare the BMS **Total** with the number of **occupied seats** (A1-A60) the seat
sensors report while the bus is at that stop. One final row per stop visit is stored in `dbo.bms_sensor_comparison`;
the frontend only reads it.

## 1. Inspection report (what the project actually has)

| Item | Finding | Consequence |
|---|---|---|
| Seat table | **`dbo.prs_sensor_readings`** (not `prs.sensor_readings`). Written by `prs_repository.insert_prs_readings`. Columns used: `id, tenant_id, vehicle_number, iot_kit, [timestamp], sensor_sub_id (=5), sensor_data ("unique_number:A1,reading:occupied"), lat, [long]`. | Reused. No snapshot table created. |
| Sensor ingestion | S3 `PRS_<kit>_<dd-mm-yyyy>_<HH-MM-SS>.csv` -> `start_prs_polling_worker` (every `PRS_POLL_INTERVAL` = 10 s) -> one file = 60 rows -> GPS from the vendor API (one position per file). | The comparison **does not poll anything**; it reads what this worker stored. |
| Batch identifier | **None existed.** | Migration 003 adds `snapshot_id UNIQUEIDENTIFIER NULL`; `insert_prs_readings` writes one id per file (only if the column exists). Old rows fall back to grouping by (tenant, vehicle, kit, timestamp). |
| Device | `dbo.prs_sensor_readings` has no `device_id`; it comes from `dbo.vehicles` (tenant + vehicle_number -> device_id). | `list_active_vehicles` joins `bms_stop_details` to `dbo.vehicles` on tenant, vehicle number and device. |
| Journey / trip id | **None existed.** | Smallest safe change: new table `dbo.bms_journeys` (see 4). `bms_stop_details` is not touched. |
| Auth / tenant | `X-Tenant-ID` header via `app.core.tenant.get_tenant_id` (marked temporary in the code). | New endpoints use it too; every query is tenant-filtered. Swap to JWT in one place later. |
| DB access | `app.database.sensor_connection.get_db_connection` (pyodbc, SQL Server). | Reused. |
| Workers | Plain threads started from `app/main.py` lifespan. | New `BMS-Comparison-Worker` thread, same style. |
| `dbo.bms_stop_details` | Not in the repo (you said it exists). Migration 004 creates it **only if missing**; rows are never modified. | |

## 2. Run order

1. `migrations/003_prs_snapshot_id.sql` (adds `snapshot_id` + 2 indexes to `prs_sensor_readings`; non-destructive)
2. `migrations/004_create_bms_tables.sql` (`bms_journeys`, `bms_vehicle_state`, `bms_sensor_comparison`)
3. DEV/TEST database only: `005_dev_seed_bms_stop_details.sql` (the 5 sample stops; edit tenant/vehicle/device first) and
   `006_dev_demo_comparison_data.sql` (demo rows in a `DEMO` journey; refuses to run unless the DB name contains test/dev).
4. Deploy the code. The worker starts with the app (`BMS_COMPARISON_ENABLED=true`).

Check your real tenant / `device_id` / `iot_kit` against `dbo.vehicles` before seeding. The sample coordinates must be
validated against where the bus really stops.

## 3. Worker behaviour (every `BMS_WORKER_INTERVAL_SECONDS`, default 10)

Per vehicle (vehicles with BMS stops and a matching `dbo.vehicles` row), vehicles in parallel, never overlapping for the same vehicle:

1. Load the persisted state row (`dbo.bms_vehicle_state`): cursor (last processed snapshot time/key), previous 60-seat state, current stop visit.
2. Read rows with `timestamp` newer than the cursor; group into 60-seat snapshots by `snapshot_id`.
3. Validate: exactly A1..A60 once each, each `occupied`/`not_occupied` (`no_data` is unusable, **a missing seat is never treated as empty**), single tenant/vehicle, IoT kit equals the BMS kit (punctuation/case ignored), valid GPS, fresh timestamp.
4. Ignore duplicates / out-of-order (timestamp <= cursor), stale (older than `BMS_MAX_SNAPSHOT_AGE_SECONDS`) and future-dated snapshots.
5. Feed each remaining snapshot, oldest first, through the stop state machine; save the state after each one.
6. When a stop visit ends, **one transaction** inserts the comparison row, saves the state and (after the last stop) closes the journey. Any failure rolls everything back; the next cycle re-reads the same snapshots (safe retry). A restart simply reloads the state.
7. Two backend processes cannot both win: the state row has a version (optimistic lock) and the comparison table has a unique key.

## 4. GPS matching and stop states

Distance = haversine of **latitude and longitude** in metres (same quantity as `geography::Point(...).STDistance`).
Exact lat/long equality is never used.

| Setting | Default | Meaning |
|---|---|---|
| `BMS_ENTRY_RADIUS_M` | 50 | inside = at the stop |
| `BMS_EXIT_RADIUS_M` | 70 | outside = left (hysteresis, stops GPS jitter splitting a visit) |
| `BMS_APPROACH_RADIUS_M` | 300 | inside = APPROACHING |
| `BMS_MIN_CONSECUTIVE_HITS` | 2 | consecutive readings inside the entry radius to ARRIVE |
| `BMS_MIN_DWELL_SECONDS` | 25 | stay this long, otherwise it was a pass-by (nothing stored) |
| `BMS_DEPARTURE_CONSECUTIVE_READINGS` | 2 | consecutive readings outside the exit radius to DEPART |

Phases: `NOT_REACHED -> APPROACHING -> STOP_CANDIDATE -> ARRIVED -> DWELLING -> DEPARTED -> COMPLETED`.
The comparison is stored when the bus departs after dwelling. Between the entry and exit radius the state is held.
Two eligible stops inside the entry radius = ambiguous, nothing selected. Only stops after the last completed one are eligible;
`BMS_ALLOW_SKIPPED_STOPS=false` enforces strict order 1..5. A skipped stop is stored as `INCOMPLETE` (not a mismatch).
If no data arrives for `BMS_VISIT_TIMEOUT_SECONDS` during a visit that already dwelled, it is closed as `INCOMPLETE`.

**Journeys.** The worker creates a journey (`bms_journeys`, status `ACTIVE`) when the vehicle first reaches a stop, closes it as
`COMPLETED` after the last stop, and marks it `ABANDONED` after `BMS_JOURNEY_MAX_IDLE_HOURS` without progress. The unique key of
`bms_sensor_comparison` is `(tenant_id, vehicle_number, device_id, journey_id, stop_sequence)`, so the same stop rows are reused by every journey.

> **Calibration warning.** The "nearby Tuni" example in the brief (17.3650000, 82.5450000) is **~438 m** from the Tuni stop
> (17.3685600, 82.5432300). It will NOT match with 50/70 m radii. Either the sample BMS coordinates or the radii
> (`BMS_ENTRY_RADIUS_M`, `BMS_EXIT_RADIUS_M`, `BMS_APPROACH_RADIUS_M`) must be calibrated with real GPS from a stopped bus.
> `GET /api/bms-sensor/tracking` shows the phase of each vehicle to help with that.

## 5. Sensor In / Out / Total

* `sensor_total` = number of occupied seats in the last valid complete snapshot of the visit (primary comparison).
* `sensor_in` / `sensor_out` = seat transitions between consecutive complete snapshots during the visit, starting from the last snapshot before the visit (`not_occupied -> occupied` = In, `occupied -> not_occupied` = Out). **They are estimates**: a passenger changing seat counts as one Out and one In. They are NULL if no earlier snapshot existed when the visit began.
* `total_difference = sensor_total - bms_total`.
* `MATCH` / `MISMATCH` only for valid data; `INCOMPLETE` when there was no valid snapshot, the last valid one is more than `BMS_MAX_VALID_GAP_SECONDS` older than the end of the visit, the stop was not visited, or the visit timed out.

## 6. API (all GET, header `X-Tenant-ID` required, tenant-filtered)

| Path | Filters |
|---|---|
| `/api/bms/stops` | `vehicle_number, device_id, journey_id` (with `journey_id` each stop carries that journey's `comparison_id` / `comparison_status`) |
| `/api/bms-sensor/comparisons` | `vehicle_number, device_id, journey_id, stop_sequence, comparison_status, page, page_size (<=200)` |
| `/api/bms-sensor/comparisons/{id}` | - (404 if not found for this tenant) |
| `/api/bms-sensor/tracking` | `vehicle_number, device_id` - live phase per vehicle |

`tenant_id` is deliberately NOT a query parameter (it would let a caller read another tenant); it comes from the header.

```json
{
  "success": true, "page": 1, "page_size": 50, "total": 2, "count": 2,
  "note": "sensor_in and sensor_out are ESTIMATES ...",
  "items": [{
    "id": 12, "tenant_id": 1, "vehicle_number": "AP31Z0044", "device_id": 1215, "iot_kit": "IOT-KIT-001", "journey_id": 3,
    "stop": {"bms_stop_id": 2, "stop_sequence": 2, "stop_name": "Tuni APSRTC Bus Station", "lat": 17.36856, "long": 82.54323},
    "bms": {"in": 6, "out": 1, "total": 17},
    "sensor": {"in": 5, "out": 1, "total": 16, "lat": 17.36874, "long": 82.54323,
               "timestamp": "2026-11-16T10:00:50", "in_out_is_estimate": true},
    "total_difference": -1, "comparison_status": "MISMATCH", "created_at": "2026-11-16T10:01:12.123000"
  }]
}
```

## 7. Frontend guidance

* Call `GET /api/bms-sensor/comparisons?journey_id=<id>` (or without `journey_id` for history) and render rows as returned; **do not recompute** MATCH/MISMATCH or the difference.
* Columns: Stop, BMS In/Out/Total, Sensor In/Out/Total, Difference (`+n`/`-n`), Status chip (MATCH green, MISMATCH red, INCOMPLETE grey).
* Show Sensor In/Out with an "estimated" hint (`sensor.in_out_is_estimate`); show `-` for `null`.
* Poll every 10-30 s or on page focus; rows appear only after the bus has left the stop.
* Send `X-Tenant-ID` (the existing `X-Tenant-ID` CORS header is already allowed).
* Dates are ISO-8601 strings in the sensor's local time (no timezone suffix).

## 8. Tests

`python -m pytest tests/bms` (79 tests: GPS, seat validation, transitions, state machine, worker flow incl. restart recovery,
DB failure + retry, duplicates, stale/future data, journeys, tenant isolation, GET APIs) run against an in-memory repository.
`tests/integration/test_bms_sqlserver.py` runs the real SQL against a **test** database: `BMS_TEST_DB=1` (skipped otherwise).

## 9. Known limitations

* The SQL in `bms_repository.py` and migrations 003-006 could not be executed in the development sandbox (no SQL Server): run migrations and `BMS_TEST_DB=1 pytest tests/integration/test_bms_sqlserver.py` on a test database first.
* Rows ingested before migration 003 have no `snapshot_id`; they are grouped by timestamp (valid only if all 60 rows of a file share a timestamp).
* A snapshot's GPS is the vendor position at ingestion time (one per file), not at the sensor timestamp.
* A vehicle that restarts the route without finishing the last stop keeps the old journey until `BMS_JOURNEY_MAX_IDLE_HOURS`.
* Readings outside the exit radius are not counted in the stop's In/Out (a passenger who boards in the last seconds after the bus moved is missed).
