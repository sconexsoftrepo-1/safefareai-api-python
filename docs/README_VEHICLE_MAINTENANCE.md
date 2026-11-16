# SafeFare AI – Vehicle Maintenance Module

> ## Maintenance flow (current behaviour; where it differs from §3–§5 and §8 below, this wins)
>
> **`vehicle_maintenance` is not changed** (still its 11 columns). Postponements are stored in their own table:
> run `migrations/001_create_postponements_table.sql` once (creates `dbo.vehicle_maintenance_postponements`).
>
> | Who | Can do |
> |---|---|
> | Fleet Owner | Create the schedule (`previous date + window = expected date`). View only after that. |
> | Driver (assigned vehicle) | Complete (`POST /{vehicle}/complete`) and postpone (`PATCH /{vehicle}/postpone`). |
> | Admin | View only. |
>
> | Step | What happens |
> |---|---|
> | Create | `expected = previous + window`. `postponed_date` is `null`. |
> | 15 days before, 1 week before | Alert to the **driver** if not completed. |
> | 3, 2, 1 days before | The daily job checks again; if still not completed, the driver is notified. |
> | Final day (due date) and every day after | Driver is told to complete it now or **postpone the date and give a reason**. If the driver does neither, the alert repeats **every 24 hours** (`VM_OVERDUE_REMINDER_EVERY_DAYS=1`) until it is completed or postponed. |
> | Postpone | Body `{"postponed_date": "...", "reason": "..."}` (reason required). Saved as a row in the postponements table; `vehicle_maintenance` dates are not touched. Driver and fleet owner are alerted, naming who changed it. The postponed date must be after the expected date and not in the past. |
> | After a postpone | The 15 / 7 / 3 / 2 / 1 / 0-day alerts and overdue now count from the postponed date. |
> | Complete (any day) | Body `{"done_date": "..."}`. `done_date` is saved, `previous = done_date`, `expected = done_date + window`, status = `completed`, and `postponed_date` is `null` again (the old postponement belongs to the old cycle and stays as history). |
> | After completion | Stays `completed` until 15 days before the new expected date, then the daily job sets it to `pending` and the cycle repeats. |
>
> **Who gets the alerts:** only the driver assigned to that vehicle (`vehicles.driver_id` = the driver's `users.id`; contact details come from `users`). The fleet owner is not notified unless `VM_NOTIFY_FLEET_OWNER=true`.
>
> **Assign the driver first** (a schedule cannot be created for a vehicle without one, 409):
> 1. Run `migrations/002_assign_driver_to_vehicle.sql` once, only to add `vehicles.driver_id` if the column is missing.
> 2. `GET /api/vehicle-maintenance/drivers` (Fleet Owner): the drivers who report to you (`users.parent_user_id` = your id).
> 3. `PUT /api/vehicle-maintenance/{vehicle_number}/driver` with `{"driver_id": 1204}` (Fleet Owner): sets that vehicle's one driver. This is the only write the module makes to `vehicles`, and only to `driver_id`.
>
> **Daily alerts:** once the due date has passed and there is no postponement, the driver is alerted every 24 hours (`VM_OVERDUE_REMINDER_EVERY_DAYS=1`) until they complete or postpone. If they postpone, the daily alerts wait until the postponed date has passed.
>
> Old route `PATCH /{vehicle}/expected-date` (with `expected_vehicle_maintenance_date`) still works as a postpone, but `reason` is now required.
> Alert kinds: `reminder_15d`, `reminder_7d`, `action_3d`, `action_2d`, `action_1d`, `due_today`, `overdue`, `created`, `postponed`, `completed`.
> Alert de-duplication is still in memory only (see §4): a restart on a reminder day can repeat that day's alert.

---

## 1. Integration plan (three wire-up points)

Your project wasn't available to me, so the module was written against plain interfaces. Everything project-specific is in `app/integration/`:

| # | File | What you connect |
|---|------|------------------|
| 1 | `app/integration/auth_adapter.py` → `get_current_user` | Your existing auth dependency. By default it reads `request.state.user` (dict or object with `id`/`user_id`, `role`, `tenant_id`, and optionally `authorized_tenant_ids` for admins). Role names like `"Fleet Owner"`, `fleet_owner`, `driver` and `admin` are normalised. |
| 2 | `app/integration/directory.py` | **Driver→vehicle assignment** and **notification recipients**. Three SELECT statements marked `TODO(confirm)`. The default guesses `vehicles.driver_id` and a `users` table. Replace them with your real relationships. |
| 3 | `app/integration/notifier.py` | Your notification service (push/SMS/email/in-app). The default sender only writes to the log. |

Also review `app/core/database.py`. If your project already has a pyodbc connection factory, pass it in instead of opening new connections:

```python
setup_vehicle_maintenance(app, connection_factory=your_get_connection, sender=YourSender())
```

### Mounting it in your existing `main.py`

```python
from contextlib import asynccontextmanager
from app.vehicle_maintenance_module import setup_vehicle_maintenance, shutdown_vehicle_maintenance
from app.api.vehicle_maintenance import router as vehicle_maintenance_router

@asynccontextmanager
async def lifespan(app):
    setup_vehicle_maintenance(app, include_router=False)   # services + daily scheduler
    yield
    shutdown_vehicle_maintenance(app)

app = FastAPI(lifespan=lifespan)          # keep your existing settings
app.include_router(vehicle_maintenance_router)
```

Error formatting (`{"success": false, ...}`, validation errors returned as 400) is scoped to this router through a custom route class. **No global exception handlers are added**, so your other APIs behave exactly as before.

---

## 2. Record identification (no `id` column)

* A schedule row is addressed by **(tenant_id, vehicle_number, device_id)**.
* The module keeps **one current-cycle row per (tenant_id, vehicle_number)**. Create refuses a second row with a 409.
* Create does **not** take a `device_id`. It looks the device up in `vehicles` from (tenant_id from login, vehicle_number) and stores it. Vehicle not in your tenant → 404; vehicle with more than one device → 409.
* **Limitation:** the table has no unique constraint, so uniqueness can't be *guaranteed* by the database, and I didn't add one. The module compensates in three ways:
  * Create runs `SELECT … WITH (UPDLOCK, HOLDLOCK)` inside the transaction, so two concurrent creates for the same vehicle are serialised.
  * Every UPDATE must affect exactly 1 row. If it doesn't, the transaction rolls back and returns 409.
  * If duplicate rows already exist (for example, inserted by another system), reads and writes return 409 and explain the problem rather than guessing which row to use.
* If a vehicle legitimately has rows for several devices, pass `?device_id=` on the per-vehicle endpoints.

---

## 3. Business rules implemented

| Rule | Implementation |
|---|---|
| Expected date on create | `previous + window` unless supplied. It may not be before `previous`. |
| Postpone (API 5) | Updates only `expected_vehicle_maintenance_date`, `reason` (if sent), `status`, `updated_at`. `previous_…` and `maintenance_time_window` are never touched and `done_date` stays NULL. |
| Completion (API 6) | `previous = done_date`, `expected = done_date + window` (new window if given), `done_date = NULL`, `status = pending`, all in **one transaction with a row lock**. **No comparison with the expected date**, so completion can be before, on or after it. The postponed date is never used. |
| Change window (API 7 / PUT) | `expected = previous + new_window`. |
| PUT with only `reason` | Keeps the current (possibly postponed) expected date. |
| PUT with explicit expected date | The explicit value wins over recalculation. |
| Status | `pending` if today ≤ expected; `overdue` if today > expected. Computed in Python (app timezone) on every response, and persisted by every write and by the daily scheduler. |
| Driver | Can view, postpone (**later only**, switch off with `VM_DRIVER_CAN_POSTPONE=false`) and complete **assigned** vehicles. Cannot create, PUT or change the interval (including `next_maintenance_time_window` on completion). |
| Fleet Owner | Everything within their own tenant. |
| Admin | Sees all authorised tenants in list/dashboard. Single-vehicle endpoints take `?tenant_id=`, which is checked against `authorized_tenant_ids`. |
| Tenant | Always taken from the auth context. A `tenant_id` in a request body is rejected (bodies forbid unknown fields). |

**Decisions I made that you may want to change:**

* `done_date` in the future → 400.
* `done_date` equal to the current `previous_vehicle_maintenance_date` → **409 (duplicate completion)**. Within the existing columns, this is how a repeated completion request is detected.
* `done_date` earlier than the current previous date → 400.
* On create, `status` is stored as `overdue` rather than `pending` if the expected date is already in the past. This follows the status rules in section 5.

### Data retention limitation (by design)

The table holds only the **current cycle**. Completing maintenance overwrites `previous_vehicle_maintenance_date` and resets `done_date`/`status`, so earlier cycles are **not kept**. The response to the completion call includes a `completed_cycle` object (`done_date` and `was_expected_on`) so the caller can see what was closed, but this isn't stored anywhere.

---

## 4. Notifications and scheduler

* **Reminder days:** expected −7, −4, −2, −1 and 0. They are **recomputed from the stored expected date** every time, never queued, so an old date can't fire after a postponement or early completion. Every response includes a `reminder_schedule` array.
* **Daily job** (`app/scheduler/maintenance_scheduler.py`), at `VM_SCHEDULER_RUN_AT` in `APP_TIMEZONE`:
  1. Reads all rows.
  2. Skips any row stored as `completed`.
  3. Re-reads the row under lock and syncs `pending`/`overdue`.
  4. Sends the reminder that is due today to the fleet owners and the assigned driver.
* **Overdue:** sent on day 1 overdue, then every `VM_OVERDUE_REMINDER_EVERY_DAYS` days (default 3). It is never sent more than once per day.
* **Event notices:** `created`, `rescheduled` and `completed` messages are sent after the transaction commits. If today is a reminder day for the *new* date, that reminder is sent immediately, because the daily run may already have happened.
* **One run at a time:** a non-blocking lock stops overlapping runs within a process.
* **If you already use APScheduler or Celery beat:** call `app.state.vehicle_maintenance_scheduler.run_once()` from it and set `VM_SCHEDULER_ENABLED=false`.

### Delivery guarantees: honest limits

* Deduplication is **in-memory only**. It is lost on restart and **not shared across processes or servers**.
  * Restarting on a reminder day with `VM_SCHEDULER_RUN_ON_STARTUP=true` can send that day's reminder again.
  * If the server is down at run time, that day's reminder is **missed**.
* **Run the scheduler in exactly one instance** (one uvicorn worker or one pod). Set `VM_SCHEDULER_ENABLED=false` everywhere else.
* Exactly-once or guaranteed delivery isn't possible without persistent storage, which the brief rules out. If your existing notification service deduplicates, that adds protection.

---

## 5. API reference

Base path: `/api/vehicle-maintenance`. Every response has the shape `{ "success", "message", "data" }`.

| # | Method & path | Roles | Notes |
|---|---|---|---|
| 1 | `POST /` | Owner, Admin | 201. `device_id` is not sent (looked up from `vehicle_number`). `maintenance_time_window` is optional: your value wins, otherwise the organization default (`VM_TENANT_WINDOWS`, then `VM_DEFAULT_WINDOW_DAYS`). 404 if the vehicle isn't in your tenant. 409 if a schedule already exists or the vehicle has several devices. |
| 2 | `GET /` | All | Filters: `vehicle_number`, `device_id`, `status`, `expected_date_from`, `expected_date_to`. Paging: `page`, `page_size` (max `VM_MAX_PAGE_SIZE`). |
| 8 | `GET /dashboard` | All | Current-cycle counts only. |
| 3 | `GET /{vehicle_number}` | All (driver: assigned only) | |
| 4 | `PUT /{vehicle_number}` | Owner, Admin | Partial update. Fields you don't send are kept. |
| 5 | `PATCH /{vehicle_number}/expected-date` | All (driver: assigned, later dates only) | |
| 6 | `POST /{vehicle_number}/complete` | All (driver: assigned, no interval change) | |
| 7 | `PATCH /{vehicle_number}/maintenance-window` | Owner, Admin | |

Status codes: 200, 201, 400 (validation, including bad date formats), 401, 403, 404, 409 (duplicate or conflict), 500 (generic message; details go to the log only).

### Sample flow (matches the brief)

**Create**: `POST /api/vehicle-maintenance`
```json
{"vehicle_number":"AP31Z0044","previous_vehicle_maintenance_date":"2026-09-30","maintenance_time_window":30,"reason":"Regular maintenance"}
```
```json
{"success":true,"message":"Maintenance schedule created successfully","data":{
 "tenant_id":101,"vehicle_number":"AP31Z0044","device_id":1215,
 "previous_vehicle_maintenance_date":"2026-09-30","maintenance_time_window":30,
 "expected_vehicle_maintenance_date":"2026-10-30","done_date":null,"status":"pending",
 "reason":"Regular maintenance","created_at":"2026-09-30T10:00:00","updated_at":"2026-09-30T10:00:00",
 "days_until_due":30,
 "reminder_schedule":[
  {"type":"reminder_7d","days_before":7,"label":"7 days before","date":"2026-10-23"},
  {"type":"reminder_4d","days_before":4,"label":"4 days before","date":"2026-10-26"},
  {"type":"reminder_2d","days_before":2,"label":"2 days before","date":"2026-10-28"},
  {"type":"reminder_1d","days_before":1,"label":"1 day before","date":"2026-10-29"},
  {"type":"due_today","days_before":0,"label":"Maintenance due today","date":"2026-10-30"}]}}
```

**Postpone**: `PATCH /api/vehicle-maintenance/AP31Z0044/expected-date`
```json
{"expected_vehicle_maintenance_date":"2026-11-10","reason":"Vehicle unavailable"}
```
Result: `previous` = 2026-09-30, `window` = 30, `expected` = 2026-11-10, `done_date` = null, `status` = pending. The reminders become 3, 6, 8, 9 and 10 Nov.

**Complete early**: `POST /api/vehicle-maintenance/AP31Z0044/complete`
```json
{"done_date":"2026-11-05","reason":"Engine oil and filter replaced"}
```
```json
{"success":true,"message":"Maintenance completed; next maintenance cycle scheduled","data":{
 "vehicle_number":"AP31Z0044","previous_vehicle_maintenance_date":"2026-11-05","maintenance_time_window":30,
 "expected_vehicle_maintenance_date":"2026-12-05","done_date":null,"status":"pending",
 "completed_cycle":{"done_date":"2026-11-05","was_expected_on":"2026-11-10"}, "...":"..."}}
```

**Change window**: `PATCH /api/vehicle-maintenance/AP31Z0044/maintenance-window`
```json
{"maintenance_time_window":45}
```
Result: `expected` = 2026-11-05 + 45 = **2026-12-20**.

**Dashboard**: `GET /api/vehicle-maintenance/dashboard`
```json
{"success":true,"message":"Maintenance dashboard retrieved successfully","data":{
 "as_of":"2026-11-09","total_vehicles_with_schedules":42,"pending":37,"completed":0,"overdue":5,
 "due_within_7_days":9,"due_within_4_days":5,"due_within_2_days":3,"due_within_1_day":2,"due_today":1,
 "note":"Counts reflect current-cycle data only. ..."}}
```
The "due within N days" counts are cumulative: they include today and exclude overdue rows.

**Error example**
```json
{"success":false,"message":"Maintenance schedule not found","data":null}
```

---

## 6. Running and testing

```bash
pip install -r requirements.txt        # only what your project lacks
cp .env.example .env                    # fill in credentials yourself
uvicorn main:app --reload               # stand-alone check (see QUICK_START.md)

# unit + API tests (no database needed: in-memory doubles of the repository)
pytest -q

# optional: real SQL Server TEST database only (refuses unless DB_DATABASE contains "test")
VM_TEST_DB=1 VM_TEST_VEHICLE="101|AP31Z0044|1215" pytest -q tests/integration
```

The test suite covers all 30 required cases. Tests are numbered `test_01…test_30`, plus extra edge cases.

* **Test 30** checks that no DDL appears anywhere in the module, that only the 11 existing columns are written, that only `vehicle_maintenance` and `vehicles` are referenced, and that every query is fully parameterised.
* The integration test also compares `INFORMATION_SCHEMA` before and after a run.
* Generated SQL is parsed as T-SQL when `sqlglot` is installed.

---

## 7. Files

**Created**
```
.env.example
requirements.txt
README_VEHICLE_MAINTENANCE.md
app/core/config.py, app/core/database.py              (skip if your project already has these; see §1)
app/integration/auth_adapter.py, directory.py, notifier.py
app/api/vehicle_maintenance.py
app/schemas/vehicle_maintenance.py
app/services/errors.py
app/services/vehicle_maintenance_service.py
app/services/maintenance_notification_service.py
app/repositories/vehicle_maintenance_repository.py
app/scheduler/maintenance_scheduler.py
app/utils/date_calculations.py
app/vehicle_maintenance_module.py
tests/conftest.py, tests/fakes.py
tests/test_vehicle_maintenance.py, tests/test_dates_and_schema_safety.py
tests/integration/test_sqlserver_repository.py
```
**To modify in your project:** only your `main.py`, to add the two calls in §1.

---

## 8. Database confirmation

* **0 tables created** (no history, notification or audit tables).
* **0 columns added**, **0 migrations**, and no changes to the existing table structure.
* SQL used: `SELECT`/`INSERT`/`UPDATE` on `vehicle_maintenance`, and `SELECT` on `vehicles` (plus your user/assignment tables through the directory adapter).
* The module never deletes rows. The only `DELETE` is in the opt-in integration test, which cleans up its own test row.
