---
module: Routine Alarms
user_document: documents/modules/routine_alarms.md
roles:
- users with alarm.read
permissions:
- alarm.read
apis:
- GET /api/v1/alarms/routine
- GET /api/v1/reference/alarm-types
sources:
- src/components/drive-vision/alerts/alerts-page.tsx
- src/components/drive-vision/alerts/event-detail-drawer.tsx
- src/features/drive-vision/api/fleet-service.ts
status: VERIFIED LIVE 2026-10-27 (200, 0 rows); a 503 on 2026-10-26 was not reproduced
---

# Routine Alarms — API and implementation reference

Technical companion of `documents/modules/routine_alarms.md`. For the Iris tool layer and developers; not for quoting to end users.

## 13. API
`GET /alarms/routine?from*&to*&alarmTypeIds&deviceIds&pageNumber&pageSize` → `[AlarmDto]`. `GET /alarms/routine/recent` exists but is **not used** (no time window; semantics undocumented).

## Technical details referenced by the user document

- Non-AI alarms reported by the GPS terminal (for example overspeed, SOS/emergency, power/disconnection, geofence entry/exit — the exact types come from `GET /reference/alarm-types`; NOT VERIFIED per tenant).
- Alarm rules (`/alarm-rules`) that control how alarm types are handled have no screen.
