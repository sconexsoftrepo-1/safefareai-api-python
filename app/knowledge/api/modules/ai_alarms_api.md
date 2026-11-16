---
module: AI Alarms (AI events)
user_document: documents/modules/ai_alarms.md
roles:
- users with alarm.read
permissions:
- alarm.read
apis:
- GET /api/v1/alarms/ai
- GET /api/v1/reference/alarm-types
- GET /api/v1/devices
sources:
- src/components/drive-vision/alerts/alerts-page.tsx
- src/components/drive-vision/alerts/event-detail-drawer.tsx
- src/components/drive-vision/alerts/alerts-model.ts
- src/features/drive-vision/api/fleet-service.ts
status: VERIFIED LIVE 2026-10-26
---

# AI Alarms (AI events) — API and implementation reference

Technical companion of `documents/modules/ai_alarms.md`. For the Iris tool layer and developers; not for quoting to end users.

## 13–15. API
`GET /alarms/ai?from*&to*&alarmTypeIds&deviceIds&pageNumber&pageSize` → `[AlarmDto {id, vendorAlarmId, deviceId, terminalNo, deviceName, alarmTypeId, alarmName, alarmTime, vendorAlarmTime, endedAt, severity, speedKmh, lat, lon, durationSeconds, videoUrl, imageUrl, handlingStatus}]`. `from` and `to` are required.

## Technical details referenced by the user document

- Events detected by the device's AI cameras — ADAS (forward collision, lane departure…), DSM (driver fatigue, distraction, phone, smoking…), BSD (blind spot) — with image/video evidence. The exact list of AI alarm types comes from `GET /reference/alarm-types`.
- Severity scale undocumented (raw value). Evidence links in this drawer are not filtered for placeholder hosts (GA-23). Handling is done on the Incidents tab.
