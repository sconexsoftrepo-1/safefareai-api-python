---
module: Leave Management
user_document: documents/modules/leave_management.md
roles:
- fleet users with workforce.*; drivers via My Work
permissions:
- workforce.read
- workforce.create
- workforce.update
- own.data.read (driver)
apis:
- GET /api/v1/leave-requests
- POST /api/v1/leave-requests
- POST /api/v1/leave-requests/{id}/approve
- POST /api/v1/leave-requests/{id}/reject
- GET /api/v1/driver/leave-requests
- POST /api/v1/driver/leave-requests
- POST /api/v1/driver/leave-requests/{id}/cancel
sources:
- src/components/drive-vision/operations/workforce-page.tsx
- src/components/drive-vision/operations/operations-model.ts
- src/components/drive-vision/operations/my-work-page.tsx
- src/features/drive-vision/api/operations-service.ts
- src/features/drive-vision/api/driver-app-service.ts
status: Reads VERIFIED LIVE 2026-10-29; writes IMPLEMENTED, NOT VERIFIED
---

# Leave Management — API and implementation reference

Technical companion of `documents/modules/leave_management.md`. For the Iris tool layer and developers; not for quoting to end users.

## 15. Status values
`LeaveDto.status`: PENDING, APPROVED, REJECTED, CANCELLED. Leave types as above.

## Technical details referenced by the user document

- Fleet: **Workforce → Leave** tab (`/drive-vision/workforce?tab=leave`).
- Driver: **My Work → My Leave** (`/drive-vision/my-work/leave`).
