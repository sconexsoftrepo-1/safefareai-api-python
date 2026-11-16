---
module: Workforce — availability, shifts and checklists
user_document: documents/modules/workforce_shifts.md
roles:
- users with workforce.read
permissions:
- workforce.read
- workforce.create
- workforce.update
apis:
- GET /api/v1/drivers/availability
- GET /api/v1/shifts
- GET /api/v1/leave-requests
- GET /api/v1/checklists
- GET /api/v1/checklist-template
sources:
- src/app/drive-vision/workforce/page.tsx
- src/components/drive-vision/operations/workforce-page.tsx
- src/components/drive-vision/operations/operations-model.ts
status: Reads VERIFIED LIVE 2026-10-29
---

# Workforce — availability, shifts and checklists — API and implementation reference

Technical companion of `documents/modules/workforce_shifts.md`. For the Iris tool layer and developers; not for quoting to end users.

## 13. APIs
`GET /drivers/availability?date`, `GET /shifts?driverId&from&to`, `GET /checklists`, `GET /checklist-template`.

## Technical details referenced by the user document

- Sidebar **Fleet → Workforce** (`/drive-vision/workforce`). Subtitle "Driver availability, shifts, leave and pre-trip checklists".
