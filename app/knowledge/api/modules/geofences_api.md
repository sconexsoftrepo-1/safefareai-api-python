---
module: Geofences
user_document: documents/modules/geofences.md
roles:
- users with geofence.read
permissions:
- geofence.read
- geofence.delete
- geofence.create (unused)
- geofence.update (unused)
apis:
- GET /api/v1/geofences
- DELETE /api/v1/geofences/{id}
- GET /api/v1/geofences/events
- GET /api/v1/geofences/events/summary
- GET /api/v1/voices/fence
- GET /api/v1/groups
- GET /api/v1/devices
sources:
- src/app/drive-vision/geofences/page.tsx
- src/components/drive-vision/geofences/geofences-page.tsx
- src/components/drive-vision/geofences/geofence-events.tsx
- src/components/drive-vision/geofences/geofence-model.ts
status: List, map, events, voices VERIFIED LIVE (2026-10-27/29); delete IMPLEMENTED, NOT VERIFIED; create/edit NOT IMPLEMENTED (blocked)
---

# Geofences — API and implementation reference

Technical companion of `documents/modules/geofences.md`. For the Iris tool layer and developers; not for quoting to end users.

## 13–15. API
`GET /geofences?shape` → `[GeofenceDto]` (shape AREA|LINE, bindType GROUP|DEVICE). `GET /geofences/events?from&to&geofenceId&deviceId&eventType&pageNumber&pageSize`; `/events/summary`. Unused: `POST /geofences`, `GET/PUT /geofences/{id}`.

## Technical details referenced by the user document

- Sidebar **Manage → Geofences** (`/drive-vision/geofences`). Subtitle "Zones, route lines and their alert rules".
- **Create a geofence**: NOT AVAILABLE in the app — create/edit are blocked until the backend documents rule/area/colour codes (Q2).
- Rule codes, area type and colour index meanings are undocumented → shown raw. Freshness metadata (`extend.source` "Stored data" vs "Live vendor data") shown as returned.
- Create/edit missing (GA-39). LINE freshness metadata inconsistent (#30).
