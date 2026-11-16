---
module: Reports
user_document: documents/modules/reports.md
roles:
- users with report.read
permissions:
- report.read; report.schedule (schedules — no screen)
apis:
- GET /api/v1/reports/mileage
- GET /api/v1/reports/driving
- GET /api/v1/reports/parking
- GET /api/v1/reports/media
- GET /api/v1/devices
sources:
- src/app/drive-vision/reports/page.tsx
- src/components/drive-vision/reports/reports-page.tsx
- src/components/drive-vision/reports/reports-model.ts
server_route_paths:
- /reports
status: VERIFIED LIVE (empty data) 2026-10-27; file download NOT IMPLEMENTED
---

# Reports — API and implementation reference

Technical companion of `documents/modules/reports.md`. For the Iris tool layer and developers; not for quoting to end users.

## 13–15. APIs
`GET /reports/mileage?from*&to*&deviceIds` → `[MileageDto]`; `/reports/driving`, `/reports/parking`, `/reports/media` (paged). Also in Swagger (unused): `/reports/idle`, `/reports/export`, `/report-schedules*`.

## Technical details referenced by the user document

- Sidebar **Monitor → Reports** (`/drive-vision/reports`); server menu `/reports`.
- **How can I download reports?** There is **no download/export button** in the current app (GA-17). Swagger has `GET /reports/export` and report schedules (`/report-schedules`, formats CSV/XLSX/PDF) but no screen uses them — NOT IMPLEMENTED IN FRONTEND.
- Media links rendered only for real http(s) URLs. Media `mediaType`/`triggerType` shown as raw codes (meanings undocumented).
