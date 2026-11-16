---
module: Alerts & Events — Incidents (alert handling)
user_document: documents/modules/alerts_incidents.md
roles:
- users with alarm.read; handling needs alarm.handle
permissions:
- alarm.read
- alarm.handle
apis:
- GET /api/v1/alerts
- GET /api/v1/alerts/{id}
- POST /api/v1/alerts/{id}/acknowledge
- POST /api/v1/alerts/{id}/comments
- POST /api/v1/alerts/{id}/resolve
- POST /api/v1/alerts/{id}/dismiss
- POST /api/v1/alerts/{id}/reopen
- GET /api/v1/reference/alarm-types
sources:
- src/app/drive-vision/alerts/page.tsx
- src/components/drive-vision/alerts/alerts-page.tsx
- src/components/drive-vision/alerts/incidents.tsx
- src/components/drive-vision/alerts/alerts-model.ts
- src/features/drive-vision/api/alert-service.ts
server_route_paths:
- /alarms
status: 'List and detail VERIFIED LIVE 2026-10-29; actions IMPLEMENTED, NOT VERIFIED; Assign NOT AVAILABLE (spec defect #32)'
---

# Alerts & Events — Incidents (alert handling) — API and implementation reference

Technical companion of `documents/modules/alerts_incidents.md`. For the Iris tool layer and developers; not for quoting to end users.

## 13–15. API
`GET /alerts?from&to&status&openOnly&severity&alarmTypeIds&deviceIds&driverId&assigneeUserId&kind&keyword&pageNumber&pageSize` → `[AlertRow {id, vendorAlarmId, alarmTime, endedAt, deviceId, deviceName, terminalNo, alarmTypeId, alarmName, kind, severity, speedKmh, lat, lon, address, durationSeconds, mediaStatus, handlingStatus NEW|ACKNOWLEDGED|IN_PROGRESS|RESOLVED|DISMISSED, handlingOutcome, handledBy, handledAt, driverId, driverName, assigneeUserId, assigneeName}]`. `GET /alerts/{id}` includes actions and evidence.

## Technical details referenced by the user document

- Sidebar **Safety → Alerts & Events** (`/drive-vision/alerts`); server menu `/alarms`. Tab chosen with **Alarm kind**.
| Acknowledge | "Records that you have seen the alert." | `POST /alerts/{id}/acknowledge` |
| Comment / Add comment | "Adds a note to the alert's history." (note required) | `POST /alerts/{id}/comments` |
| Resolve | "Closes the alert with an outcome." — **Outcome** required | `POST /alerts/{id}/resolve` |
| Dismiss | "Closes the alert without a resolution outcome." | `POST /alerts/{id}/dismiss` |
| Reopen | "Returns a closed alert to open handling." | `POST /alerts/{id}/reopen` |
- **Can I assign an alert to someone?** Not yet — the Swagger body for `/alerts/{id}/assign` is wrong (#32), so Assign isn't offered.
- Assign and high-priority steps (`/alerts/{id}/high-priority-steps`) not available in the UI. Alert status vs history inconsistency observed (#36).
