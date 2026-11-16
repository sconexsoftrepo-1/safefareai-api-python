---
module: Trips & Tracking
user_document: documents/modules/trips_tracking.md
roles:
- users with track.read
permissions:
- track.read
apis:
- GET /api/v1/trips
- GET /api/v1/trips/summary
- GET /api/v1/trips/{id}
- GET /api/v1/trips/{id}/route
- GET /api/v1/devices/{id}/track
- GET /api/v1/devices/{id}/event-markers
- GET /api/v1/devices
sources:
- src/app/drive-vision/trips/page.tsx
- src/components/drive-vision/trips/trips-page.tsx
- src/components/drive-vision/trips/trip-history.tsx
- src/components/drive-vision/trips/trip-model.ts
- src/components/drive-vision/trips/track-model.ts
- src/features/drive-vision/api/insight-service.ts
status: VERIFIED LIVE (read) 2026-10-29; read-only in the frontend
---

# Trips & Tracking — API and implementation reference

Technical companion of `documents/modules/trips_tracking.md`. For the Iris tool layer and developers; not for quoting to end users.

## 13–15. APIs
- `GET /trips?from&to&deviceId&driverId&pageNumber&pageSize` → `[TripDto {id, deviceId, deviceName, terminalNo, driverId, driverName, startTime, endTime, inProgress, startLat/Lon, endLat/Lon, distanceKm, durationSeconds, drivingSeconds, idleSeconds, maxSpeedKmh, avgSpeedKmh, stopCount, alarmCount}]`.
- `GET /trips/summary`, `GET /trips/{id}`, `GET /trips/{id}/route` (points, stops, events; `truncated` shown).
- `GET /devices/{id}/track?from&to` (≤ 7 days), `GET /devices/{id}/event-markers` (`video.playback` or `alarm.read`).

## Technical details referenced by the user document

- Empty track → "No points in this range"; unusable positions → "Nothing to draw"; route failure → "Couldn't load the route". An empty track may come back as 503 from the vendor (backend defect #13).
- **Can I create or edit trips?** Not in the app. (Swagger has `POST/PUT/DELETE /trips` with `trip.create/update/delete`, unused.)
