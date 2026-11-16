---
module: Notifications
user_document: documents/modules/notifications.md
roles:
- all signed-in users
permissions:
- none (any signed-in user)
apis:
- GET /api/v1/notifications
- GET /api/v1/notifications/unread-count
- POST /api/v1/notifications/{id}/read
- POST /api/v1/notifications/{id}/unread
- POST /api/v1/notifications/read-all
sources:
- src/components/drive-vision/app-shell/notification-center.tsx
- src/components/drive-vision/app-shell/search-model.ts
- src/features/drive-vision/api/alert-service.ts
status: Read VERIFIED LIVE (empty) 2026-10-29; mark read/unread IMPLEMENTED, NOT VERIFIED
---

# Notifications — API and implementation reference

Technical companion of `documents/modules/notifications.md`. For the Iris tool layer and developers; not for quoting to end users.

## 15. API
`GET /notifications?unreadOnly&type&pageNumber&pageSize` → `[NotificationDto]` with `type` ∈ ALARM, AI_EVENT, GEOFENCE, DISPATCH, LEAVE, SWAP, SHIFT, EXPIRY, MAINTENANCE, COMMAND, SENSOR, SYSTEM. `GET /notifications/unread-count` → `{unread: n}`.

## Technical details referenced by the user document

- Bell icon in the top bar (badge = unread count). Drivers use the same bell (server menu `/driver/notifications` has no page).
- **Why am I not receiving notifications?** The bell only refreshes on load or when the panel closes — reload the page. There are no push or email notifications in the web app (`/me/push-tokens` exists in Swagger for mobile push but is unused). The server decides which events notify which users (NOT DOCUMENTED).
- No polling/push (GA-20). `GET /notifications/poll` unused.
