---
module: Sensors (passenger counting, BMS reconciliation, alcohol detection)
feature_keys:
- sensors
- passenger-count
- bms
- ir-sensor
- capacity
- over-capacity
- alcohol-detection
- sensor-readings
- recalculate-stops
routes:
- /drive-vision/sensors
roles:
- users with sensor.read
permissions:
- sensor.read
- sensor.ingest
- device.read (bus picker)
availability: IMPLEMENTED, NOT VERIFIED
technical_reference: api/modules/sensors_passenger_counting_api.md
---

# Sensors — passenger counting, BMS reconciliation and alcohol check

## 1. Purpose
For buses: stop-by-stop passenger counts from the **IR door sensor** compared with the **BMS** (ground-truth boarding records), bus capacity and over-capacity, raw sensor readings, and the latest **alcohol sensor** result.

## 2. Navigation
Sidebar **Monitor → Sensors**. Subtitle "Stop-wise passenger counts, sensor vs BMS reconciliation and bus capacity".

## 3. Screen
- **Bus** picker (needs `device.read`; "Choose a bus"), **Time window (IST)**: Last 24 h · Today · Yesterday · 7 days · Custom (From/To).
- **Passenger summary**: Bus capacity, On board · BMS, On board · sensor, Latest difference, Match rate, Over-capacity stops.
- **View** tabs: *Sensor vs BMS* (Stop, BMS in/out, Actual, Sensor in/out, Difference, Status, Notes), *Stops* (Seq, Sensor reported, Boarded, Alighted, On board (BMS)), *BMS records* (BMS id …), *Sensor readings* (Type, Data, Active; filter Sensor type).
- **Alcohol check · latest reading** (Time, Sensor, Value, Result).
- Buttons **Refresh**, **Recalculate**, **Add reading**.

## 5. Buttons
| Button | Permission | Action |
|---|---|---|
| Recalculate | sensor.ingest (+tenant) | "Rebuilds stop visits from GPS and raises any new over-capacity or mismatch alerts for the selected window. Running it again changes nothing." (max 7 days) |
| Add reading | sensor.ingest (+tenant) | Stores one sensor reading |

## 6. Add sensor reading form
Sensor type, Sensor ID (e.g. IR-01; 1–100 letters, digits, dot, underscore, colon or hyphen), Time (IST; ≤ 5 min in future), data (IR: in/out/count 0–300; Alcohol: Result "Alcohol detected (1)" / "Not detected (0)"), Active reading. Duplicate identical reading → "Reading already stored"; same time different value → 409.

## 16. Business rules (contract)
- actualCount (BMS) = previous + boarded − alighted; sensorCount likewise from IR; difference = sensor − actual. `null` means UNKNOWN, never 0. Counts are "on board at that moment" — never add them across stops.
- Bus capacity = the vehicle's passenger capacity, otherwise 44 (the screen shows which one is used).
- Comparison status: MATCH (green), MISMATCH (amber), OVER_CAPACITY / OVER_CAPACITY_MISMATCH (red), NO_BMS / NO_SENSOR_COUNT (grey).
- Window default 24 h, max 31 days; lists capped at 1000 rows ("Only the first 1000 rows are shown — narrow the time window").
- Alcohol: "1" = DETECTED, "0" = NOT_DETECTED, anything else INVALID_READING, none = NO_READING. NO_READING / INVALID_READING never mean "not detected".
- Sensor alerts arrive as notifications of type `SENSOR` (PASSENGER_OVER_CAPACITY, PASSENGER_COUNT_MISMATCH, SENSOR_CHANGE).

## 18. Common questions
- **What is BMS?** The bus boarding records used as ground truth for passenger counts.
- **Why is the sensor count different from BMS?** The IR door sensor missed or double-counted passengers; see the Difference and Notes columns (e.g. SENSOR_READINGS_MISSING, BMS_SEQUENCE_GAP).
- **How do I check if a driver's alcohol test failed?** Sensors → choose the bus → *Alcohol check · latest reading*.

## 19. Limitations
The vehicle form can't set passenger capacity, so capacity is 44 unless set by an administrator through the backend. NOT VERIFIED live.
