# Quick start – check the module directly

1. Open PowerShell in this folder (safefare_vm):
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt

2. Install "ODBC Driver 18 for SQL Server" from Microsoft, if it's not already installed.

3. Make the settings file:
   copy .env.example .env
   Fill in DB_SERVER, DB_DATABASE, DB_USERNAME, DB_PASSWORD
   and DEV_TENANT_ID (a real tenant_id from your vehicles table).
   SQL Server on your own laptop -> also set DB_TRUST_SERVER_CERTIFICATE=yes

4. (Optional) run check_schema.sql in SSMS to see your columns and pick a test vehicle.

5. Start:
   uvicorn main:app --reload
   Open http://127.0.0.1:8000/docs

6. On every endpoint you can fill X-Dev-Role (fleet_owner / driver / admin),
   X-Dev-User-Id and X-Dev-Tenant-Id. Leave them blank to use the .env values.

Suggested order:
   POST  /api/vehicle-maintenance                      create (expected = previous + window)
   PATCH /api/vehicle-maintenance/{vehicle}/postpone         postpone (driver only: postponed_date + reason)
   POST  /api/vehicle-maintenance/{vehicle}/complete        complete (driver only: done_date)
   POST  /dev/run-scheduler                            reminders print in the terminal

Automated tests (no database needed):  pytest -q

main.py replaces real login with test headers. It's for checking only; never deploy it.
To use the module inside your real project, see README_VEHICLE_MAINTENANCE.md section 1.
