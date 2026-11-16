---
module: Driver Assignments (driver ↔ vehicle)
user_document: documents/modules/driver_assignments.md
roles:
- users with driver.update to change; driver.read to view
permissions:
- driver.update
- driver.read
- device.read
apis:
- POST /api/v1/drivers/{id}/assignments
- POST /api/v1/drivers/{id}/assignments/{assignmentId}/end
- GET /api/v1/drivers/{id}/assignments
- GET /api/v1/devices/{id}/driver-assignments
- GET /api/v1/driver/assignment
sources:
- src/components/drive-vision/drivers/drivers-page.tsx
- src/components/drive-vision/drivers/drivers-model.ts
- src/components/drive-vision/vehicles/vehicle-operations.tsx
status: Reads VERIFIED LIVE 2026-10-29; assign/end IMPLEMENTED, NOT VERIFIED
---

# Driver Assignments (driver ↔ vehicle) — API and implementation reference

Technical companion of `documents/modules/driver_assignments.md`. For the Iris tool layer and developers; not for quoting to end users.

## 13–15. API
`POST /drivers/{id}/assignments` body `AssignRequest {deviceId*, from, to, replaceCurrent}` → `AssignmentDto`. `POST …/assignments/{assignmentId}/end`.

## Technical details referenced by the user document

- Driver app: My Work → Today → Vehicle (`GET /driver/assignment`).
- Overlapping assignments are rejected by the server unless `replaceCurrent`. Alarms show the driver **as reported by the server**; the app never derives an alarm's driver from the current assignment.
- Writes not verified live. `AssignRequest` schema is shared with alert assignment in Swagger (spec defect #32).
