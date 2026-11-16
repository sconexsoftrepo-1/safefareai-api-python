---
module: Driver application — My Work (driver self-service)
user_document: documents/modules/driver_my_work.md
roles:
- Driver (role DRIVER, not platform) linked to a driver profile
permissions:
- driver.app
- own.data.read
apis:
- GET /api/v1/driver/me
- PATCH /api/v1/driver/me
- GET /api/v1/driver/assignment
- GET /api/v1/driver/dispatches
- GET /api/v1/driver/dispatches/{id}
- POST /api/v1/driver/dispatches/{id}/accept
- POST /api/v1/driver/dispatches/{id}/start
- POST /api/v1/driver/dispatches/{id}/complete
- POST /api/v1/driver/dispatches/{id}/decline
- POST /api/v1/driver/dispatches/{id}/swap-requests
- GET /api/v1/driver/shifts/current
- POST /api/v1/driver/shifts/start
- POST /api/v1/driver/shifts/end
- GET /api/v1/driver/working-hours
- GET /api/v1/driver/leave-requests
- POST /api/v1/driver/leave-requests
- POST /api/v1/driver/leave-requests/{id}/cancel
- GET /api/v1/driver/checklist-template
- GET /api/v1/driver/checklists
- POST /api/v1/driver/checklists
- GET /api/v1/driver/safety-score
- GET /api/v1/driver/safety-events
- POST /api/v1/me/password
sources:
- src/app/drive-vision/my-work/page.tsx
- src/app/drive-vision/my-work/shifts/page.tsx
- src/app/drive-vision/my-work/leave/page.tsx
- src/app/drive-vision/my-work/checklist/page.tsx
- src/app/drive-vision/my-work/safety/page.tsx
- src/app/drive-vision/my-work/profile/page.tsx
- src/components/drive-vision/operations/my-work-page.tsx
- src/components/drive-vision/operations/my-work-model.ts
- src/components/drive-vision/operations/my-work-ui.tsx
- src/features/drive-vision/api/driver-app-service.ts
server_route_paths:
- /driver/work
- /driver/shifts
- /driver/leave
- /driver/checklist
- /driver/safety
- /driver/profile
- /driver/notifications
status: Reads VERIFIED LIVE with a Driver login 2026-10-29 (9 GETs); driver writes IMPLEMENTED, NOT VERIFIED. This is a responsive web section, not a native mobile app.
---

# Driver application — My Work (driver self-service) — API and implementation reference

Technical companion of `documents/modules/driver_my_work.md`. For the Iris tool layer and developers; not for quoting to end users.


## Technical details referenced by the user document

| My Work (Today) | `/drive-vision/my-work` | Today, current/next trip, upcoming trips |
| My Shifts | `/drive-vision/my-work/shifts` | "Your current shift and working hours" |
| My Leave | `/drive-vision/my-work/leave` | "Your leave requests and their status" |
| Shift Checklist | `/drive-vision/my-work/checklist` | "Pre-trip vehicle checklist and your recent submissions" |
| My Safety | `/drive-vision/my-work/safety` | "Your safety score and recent events" |
| My Profile | `/drive-vision/my-work/profile` | "Your contact details and licence" |
- The server resolves "me" from the token; the app never sends a driver id. `/driver/**` returns only that driver's data.
- Drivers cannot open fleet screens (Fleet Overview, Live Monitoring, Drivers, etc.); the server refused the Driver token on every fleet GET tested (GA-01 PASS, 2026-10-31).
- Driver writes untested live; driver preferences not available; Iris assistant (Java `/assistant/*`) needs `device.read`, so drivers don't get the current assistant.
