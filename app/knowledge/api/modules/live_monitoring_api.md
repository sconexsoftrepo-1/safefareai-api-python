---
module: Live Monitoring
user_document: documents/modules/live_monitoring.md
roles:
- any user with device.read
permissions:
- device.read
apis:
- GET /api/v1/monitor/realtime
- GET /api/v1/devices
- GET /api/v1/groups
sources:
- src/app/drive-vision/monitoring/page.tsx
- src/components/drive-vision/monitoring/live-monitoring.tsx
- src/components/drive-vision/monitoring/live-device-panel.tsx
- src/components/drive-vision/monitoring/live-fleet-model.ts
- src/components/drive-vision/monitoring/live-video-dialog.tsx
- src/components/drive-vision/monitoring/gps-video.ts
- src/components/drive-vision/map/geo-map.tsx
- src/components/drive-vision/map/base-map-config.ts
status: VERIFIED LIVE 2026-10-26 (map, list, polling, panel); live camera popup depends on vendor token (NOT VERIFIED)
---

# Live Monitoring — API and implementation reference

Technical companion of `documents/modules/live_monitoring.md`. For the Iris tool layer and developers; not for quoting to end users.

## 13–15. APIs
`GET /monitor/realtime?deviceIds` → `RealtimeDto {onlineCount, offlineCount, devices:[DeviceStateDto {deviceId, name, terminalNo, statusCode, deviceTime, lat, lon, speedKmh, directionDeg, altitudeM, mileageKm, batteryPct, gsmSignal, networkType, activeAlarm, videoCapable, sensors, receivedAt}]}`. Polled every 30 s while the tab is visible (env `NEXT_PUBLIC_REALTIME_POLL_MS`, minimum 10 s; the vendor answers 503 if polled too often).

## Technical details referenced by the user document

- Online/offline totals are the server's counts; the undocumented `statusCode` is never used for colours or filters.
- **Watch live camera**: pick the device → the Live video popup opens (vendor player, channels 1..camera count). If it says "Live video unavailable", the device has no terminal number or live video isn't configured (`NEXT_PUBLIC_GPS_VIDEO_API_TOKEN`).
- There is **no online/offline filter** on this screen. The Fleet Overview "Offline" tile links to `/drive-vision/monitoring?status=offline`, but this page ignores the `status` parameter (frontend inconsistency, see `limitations.md`). To find offline devices use the "Stale" report-age filter as an approximation, or ask Iris (live data).
- No push updates; polling only (GA-36).
- Live video uses a public vendor token in the browser bundle; `GET /video/embed` and `/video/sdk-token` in Swagger are unused.
