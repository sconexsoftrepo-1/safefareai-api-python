---
module: Sensors (passenger counting, BMS reconciliation, alcohol detection)
user_document: documents/modules/sensors_passenger_counting.md
roles:
- users with sensor.read
permissions:
- sensor.read
- sensor.ingest
- device.read (bus picker)
apis:
- GET /api/v1/sensors/types
- POST /api/v1/sensors/readings
- GET /api/v1/devices/{id}/sensors/readings
- GET /api/v1/devices/{id}/stops
- GET /api/v1/devices/{id}/bms
- GET /api/v1/devices/{id}/stops/comparison
- GET /api/v1/devices/{id}/passenger-summary
- POST /api/v1/devices/{id}/stops/recalculate
- GET /api/v1/devices/{deviceId}/sensors/alcohol
sources:
- src/app/drive-vision/sensors/page.tsx
- src/components/drive-vision/sensors/sensors-page.tsx
- src/components/drive-vision/sensors/sensors-model.ts
- src/features/drive-vision/api/sensor-service.ts
- docs/contracts/passenger-counting-api.txt
- docs/contracts/alcohol-detection-api.txt
server_route_paths:
- /sensors
status: IMPLEMENTED from backend contracts dated 2026-11-03 (now in provided Swagger). Live use NOT VERIFIED in repo evidence.
---

# Sensors (passenger counting, BMS reconciliation, alcohol detection) — API and implementation reference

Technical companion of `documents/modules/sensors_passenger_counting.md`. For the Iris tool layer and developers; not for quoting to end users.


## Technical details referenced by the user document

- Sidebar **Monitor → Sensors** (`/drive-vision/sensors`). Subtitle "Stop-wise passenger counts, sensor vs BMS reconciliation and bus capacity".
| Recalculate | sensor.ingest (+tenant) | `POST /devices/{id}/stops/recalculate` — "Rebuilds stop visits from GPS and raises any new over-capacity or mismatch alerts for the selected window. Running it again changes nothing." (max 7 days) |
| Add reading | sensor.ingest (+tenant) | `POST /sensors/readings` with one reading |
- Sensor type (from `/sensors/types`), Sensor ID (e.g. IR-01; 1–100 chars `[A-Za-z0-9._:-]`), Time (IST; ≤ 5 min in future), data (IR: in/out/count 0–300; Alcohol: Result "Alcohol detected (1)" / "Not detected (0)"), Active reading. Duplicate identical reading → "Reading already stored"; same time different value → 409.
- Bus capacity = vehicle `passengerCapacity`, else 44 (`capacitySource` VEHICLE | DEFAULT).
- `comparisonStatus`: MATCH (green), MISMATCH (amber), OVER_CAPACITY / OVER_CAPACITY_MISMATCH (red), NO_BMS / NO_SENSOR_COUNT (grey).
- Vehicle form can't set `passengerCapacity`, so capacity is 44 unless set via API. NOT VERIFIED live.
