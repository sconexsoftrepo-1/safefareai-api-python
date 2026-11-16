# SafeFare Backend (Iris AI + IoT Sensors + Tyre Maintenance + Vehicle Maintenance)

One FastAPI app that serves the Iris AI chat API, the IoT Sensor ingestion API, the Tyre Maintenance API and the Vehicle Maintenance API.

## Run

```bash
python -m venv venv
venv\Scripts\activate          # Windows  (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
uvicorn app.main:app --reload  # run from this folder (where .env is)
```

Swagger UI: http://127.0.0.1:8000/docs

### Local (localhost) testing

* `ROOT_PATH` now defaults to empty, so everything is served at `http://127.0.0.1:8000/...` (no `/safe-fare-python` prefix).
  On the server set `ROOT_PATH=/safe-fare-python` in `.env`.
* CORS already allows `http://localhost:3000`, `:5173`, `:8000` and the `127.0.0.1` forms; add more with `CORS_EXTRA_ORIGINS`.
* Run with `run_local.bat` (Windows) / `./run_local.sh`, or `python -m app.main`.
* The tenant for the tyre / BMS endpoints is the `X-Tenant-ID` header (Swagger "Try it out" shows the field).

## Endpoints

| Method | Path | From |
|---|---|---|
| GET | `/` | combined |
| GET | `/health` | Iris AI |
| POST | `/api/chat/message` | Iris AI |
| GET | `/api/sensors/health` | Sensor |
| GET | `/api/sensors/database/test` | Sensor |
| POST | `/api/sensors/process-s3` | Sensor |
| GET | `/api/sensors/alerts?tenant_id=&vehicle_number=` | Sensor |
| GET | `/api/v1/tyre-maintenance` | Tyre (needs `X-Tenant-ID` header) |
| GET | `/api/v1/tyre-maintenance/alerts` | Tyre |
| GET | `/api/v1/tyre-maintenance/vehicle/{vehicle_number}` | Tyre |
| POST | `/api/v1/tyre-maintenance/vehicle/{vehicle_number}/register` | Tyre |
| POST | `/api/v1/tyre-maintenance/vehicle/{vehicle_number}/complete` | Tyre |
| GET | `/api/bms/stops` | BMS vs Sensor (needs `X-Tenant-ID`) |
| GET | `/api/bms-sensor/comparisons` | BMS vs Sensor (needs `X-Tenant-ID`) |
| GET | `/api/bms-sensor/comparisons/{id}` | BMS vs Sensor (needs `X-Tenant-ID`) |
| GET | `/api/bms-sensor/tracking` | BMS vs Sensor (needs `X-Tenant-ID`) |
| GET, POST | `/api/vehicle-maintenance` | Vehicle Maintenance |
| GET | `/api/vehicle-maintenance/alerts` | Vehicle Maintenance |
| GET | `/api/vehicle-maintenance/{vehicle_number}` | Vehicle Maintenance |
| POST | `/api/vehicle-maintenance/{vehicle_number}/complete` | Vehicle Maintenance |
| PATCH | `/api/vehicle-maintenance/{vehicle_number}/postpone` | Vehicle Maintenance |

On startup three background jobs start automatically: the S3 polling worker (Sensor), the tyre maintenance
scheduler (Tyre) and the daily vehicle maintenance scheduler (Vehicle Maintenance, `VM_SCHEDULER_*` in `.env`).
Run the app as a single instance, otherwise the schedulers run twice.

## What changed during the merge (no business logic changed)

1. **`app/main.py`**: one file that registers both routers, the Sensor startup worker and logging.
2. **Sensor `database/connection.py` → `app/database/sensor_connection.py`**: renamed because Iris already has
   `app/database/connection.py`. Only the import line was updated in `sensor_repository.py`,
   `vehicle_mapping.py`, `iot_kit_monitoring_service.py` and `sensor_routes.py`.
3. **One `.env`**: both projects used `DB_NAME`, `DB_USERNAME`, etc. but for *different* databases
   (`Safe-Fare-Python` for Iris, `Safe-Fare` for Sensor). The Sensor ones are now `SENSOR_DB_*`, and
   `app/config/settings.py` reads those names. Iris variables are unchanged.
4. **`requirements.txt`**: merged, plus `openai`, `groq`, `faiss-cpu`, `numpy` and `sentence-transformers`,
   which Iris imports but its old requirements file left out.
5. Sensor's `test.py` is now `test_sensor_upload.py` (Iris already had a `test.py`).

## What changed when Tyre and Vehicle Maintenance were merged in

No business logic was changed in either module. Only names that clashed were changed.

1. **`app/main.py`**: registers the two new routers and starts/stops both new schedulers in the same `lifespan`.
2. **Vehicle Maintenance `core/config.py` -> `app/core/vm_config.py`**, **`core/database.py` -> `app/core/vm_database.py`**
   (Iris already owns `app/core/config.py`; Tyre owns `app/core/database.py`). Only the import lines were updated.
3. **Vehicle Maintenance env vars**: it used `DB_SERVER`, `DB_DATABASE`, ... which clash with the Iris `DB_*` settings
   (a different database). They are now `VM_DB_*` and `VM_APP_TIMEZONE`. All other `VM_*` names are unchanged.
   Tyre keeps `SQL_CONNECTION_STRING`, `TYRE_MAINTENANCE_CHECK_INTERVAL`, `TYRE_OVERDUE_REMINDER_INTERVAL_HOURS`.
4. **Vehicle Maintenance dev login**: the "pretend logged-in user" that lived in its own `main.py` is now
   `app/integration/dev_auth.py`, switched on by `DEV_TENANT_ID` in `.env` exactly as before.
   **Remove `DEV_TENANT_ID` before deploying.**
5. **`/` and `/health`** are the existing Iris/Sensor ones. Tyre's standalone `/health` (which also returned
   `"service": "SafeFare API"`) is not registered because the path was already taken.
6. SQL scripts are in `migrations/`, the original Vehicle Maintenance docs in `docs/`, its tests in `tests/`.
7. `requirements.txt`: added `tzdata` (needed by the Vehicle Maintenance scheduler on Windows).

BMS vs Sensor comparison (added): see `docs/BMS_SENSOR_COMPARISON.md` - migrations 003-006, worker, GPS logic, API, frontend guide.
