---
module: Historical Video
user_document: documents/modules/historical_video.md
roles:
- users with video.playback
permissions:
- video.playback (screen and export request)
- video.live (live/embed — unused)
apis:
- GET /api/v1/devices
- GET /api/v1/devices/{id}/recording-calendar
- GET /api/v1/devices/{id}/recordings
- GET /api/v1/video/exports
- POST /api/v1/video/exports
sources:
- src/app/drive-vision/video/page.tsx
- src/components/drive-vision/video/video-workspace.tsx
- src/components/drive-vision/video/recording-calendar.tsx
- src/components/drive-vision/video/video-model.ts
- src/features/drive-vision/api/fleet-service.ts
status: PARTIALLY IMPLEMENTED — calendar, recordings list and export list VERIFIED LIVE (empty data, 2026-10-27); export request NOT VERIFIED; PLAYBACK NOT AVAILABLE (vendor SDK missing)
---

# Historical Video — API and implementation reference

Technical companion of `documents/modules/historical_video.md`. For the Iris tool layer and developers; not for quoting to end users.

## 13–15. APIs
- `GET /devices/{id}/recording-calendar?month=YYYY-MM` → list of integers (treated as days of month — NOT VERIFIED contract).
- `GET /devices/{id}/recordings?from&to&channel` (IST day window).
- `GET /video/exports?deviceId` (paged) → `ExportDto` (status shown raw).
- `POST /video/exports` body `ExportRequest` (dataType/streamType not sent).
Unused in Swagger: `GET /video/sdk-token`, `GET /video/embed`, `GET /video/exports/{id}`.

## Technical details referenced by the user document

- Sidebar **Monitor → Historical Video** (`/drive-vision/video`).
| Export clip (on a recording) → **Request export** | `POST /video/exports` for that recording segment, after confirmation "Request a clip export?". |
- Exports may consume vendor credit or device data — NOT VERIFIED (Q3).
- PLAYBACK NOT AVAILABLE (GA-08). Export status values and cost undocumented. No auto-refresh of export status (GA-35).
