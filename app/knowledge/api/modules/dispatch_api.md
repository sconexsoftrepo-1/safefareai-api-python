---
module: Dispatch
user_document: documents/modules/dispatch.md
roles:
- users with dispatch.read
permissions:
- dispatch.read
- dispatch.create
- dispatch.update
apis:
- GET /api/v1/dispatches
- GET /api/v1/dispatches/{id}
- POST /api/v1/dispatches
- PUT /api/v1/dispatches/{id}
- POST /api/v1/dispatches/check
- POST /api/v1/dispatches/{id}/cancel
- GET /api/v1/dispatches/{id}/verification
- GET /api/v1/dispatches/conflicts
- GET /api/v1/swap-requests
- POST /api/v1/dispatches/{id}/swap-requests
- POST /api/v1/swap-requests/{id}/approve
- POST /api/v1/swap-requests/{id}/reject
sources:
- src/app/drive-vision/dispatch/page.tsx
- src/components/drive-vision/operations/dispatch-page.tsx
- src/components/drive-vision/operations/operations-model.ts
- src/components/drive-vision/operations/use-pickers.ts
- src/features/drive-vision/api/operations-service.ts
status: List, conflicts, swaps VERIFIED LIVE (empty) 2026-10-29; detail/verification not observed; writes IMPLEMENTED, NOT VERIFIED
---

# Dispatch — API and implementation reference

Technical companion of `documents/modules/dispatch.md`. For the Iris tool layer and developers; not for quoting to end users.


## Technical details referenced by the user document

- Sidebar **Fleet → Dispatch** (`/drive-vision/dispatch`). Subtitle "Dispatched trips, conflict checks and driver swaps".
- 3. **Check conflicts** (`POST /dispatches/check`, creates nothing). Result: "No conflicts found" or "The server reported conflicts".
- Writes not verified live; whether creating a dispatch sends SMS/push to the driver is NOT VERIFIED (#37).
