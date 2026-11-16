---
module: Notifications
feature_keys:
- notifications
- notification-bell
- unread-count
- mark-read
- mark-all-read
routes:
- header bell (every screen)
roles:
- all signed-in users
permissions:
- none (any signed-in user)
availability: Read VERIFIED (empty)
technical_reference: api/modules/notifications_api.md
---

# Notifications

## 1. Purpose
In-app notifications for the signed-in user (alarms, AI events, geofence events, dispatches, leave, swaps, shifts, expiries, maintenance, commands, sensors, system).

## 2. Navigation
Bell icon in the top bar (badge = unread count). Drivers use the same bell.

## 3. Panel
List of notifications (newest first), each opening its related page when the user may open it; per-item mark read/unread; **Mark all as read**; footer "Open Alerts & Events" (fleet users); empty state "No notifications — You're all caught up."

## 4. Notification types
Alarm, AI event, Geofence, Dispatch, Leave, Swap, Shift, Expiry, Maintenance, Command, Sensor and System notifications. Each opens its related page when you are allowed to open it.

## 9. Workflows
**Show recent notifications**: select the bell. **Mark all read**: bell → Mark all as read.

## 16. Business rules
- The count is read on page load and when the panel closes — **no polling or push** (the badge can be stale).
- Links: leave → Workforce › Leave (fleet) or My Leave (driver); swaps → Dispatch › Swap requests (fleet) or My Work (driver); otherwise the related record page if the user can open it.

## 18. Common questions
- **Why am I not receiving notifications?** The bell only refreshes on load or when the panel closes — reload the page. There are no push or email notifications in the web app. The server decides which events notify which users (NOT DOCUMENTED).

## 19. Limitations
No automatic refresh or push notifications.
