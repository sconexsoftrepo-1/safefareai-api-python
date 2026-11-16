---
title: Permission code to API operations
category: api
source: provided Swagger "Required permission" lines
---

# Permission code → API operations (generated from the Swagger)

Use this to check, before calling a tool, that the signed-in user holds the code the endpoint needs. The Java backend still enforces it.
| Permission code | Operations requiring it |
|---|---|
| `(any signed-in user)` | DELETE /me/push-tokens; GET /me; GET /me/menus; GET /me/permissions; GET /me/preferences; GET /me/push-tokens; GET /notifications; GET /notifications/poll; GET /notifications/unread-count; GET /reference/alarm-types; GET /reference/device-models; GET /reference/object-types; GET /reference/protocols; GET /reference/statuses; PATCH /me; POST /auth/logout; POST /me/password; POST /me/push-tokens; POST /notifications/read-all; POST /notifications/{id}/read; POST /notifications/{id}/unread; PUT /me/preferences |
| `alarm.handle` | POST /alerts/{id}/acknowledge; POST /alerts/{id}/assign; POST /alerts/{id}/comments; POST /alerts/{id}/dismiss; POST /alerts/{id}/high-priority-steps; POST /alerts/{id}/reopen; POST /alerts/{id}/resolve |
| `alarm.read` | GET /alarms/ai; GET /alarms/routine; GET /alarms/routine/recent; GET /alerts; GET /alerts/{id}; GET /alerts/{id}/actions; GET /alerts/{id}/evidence; GET /alerts/{id}/high-priority-steps; GET /dashboard/safety-events; GET /devices/{id}/event-markers; GET /drivers/{id}/safety-events; GET /drivers/{id}/safety-score; GET /safety/analytics; GET /safety/false-positives; GET /safety/heatmap; GET /safety/scores/drivers; GET /safety/scores/vehicles |
| `alarm.rule.create` | POST /alarm-rules |
| `alarm.rule.delete` | DELETE /alarm-rules/{id} |
| `alarm.rule.read` | GET /alarm-rules; GET /alarm-rules/{id} |
| `alarm.rule.update` | PUT /alarm-rules/{id} |
| `audit.read` | GET /audit-logs |
| `command.send` | GET /commands; GET /commands/types; GET /commands/{id}; POST /commands |
| `device.create` | POST /devices |
| `device.delete` | DELETE /devices/{id} |
| `device.read` | GET /assets/tree; GET /assistant/prompts; GET /dashboard/active-trips; GET /dashboard/device-health; GET /dashboard/fleet-health; GET /dashboard/fleet-status; GET /dashboard/overview; GET /dashboard/trends; GET /dashboard/vehicles; GET /devices; GET /devices/{id}; GET /devices/{id}/passthrough-data; GET /devices/{id}/summary; GET /monitor/realtime; GET /search; POST /assistant/ask |
| `device.update` | POST /devices/transfer; PUT /devices/{id} |
| `dispatch.create` | POST /dispatches |
| `dispatch.read` | GET /dispatches; GET /dispatches/conflicts; GET /dispatches/{id}; GET /dispatches/{id}/verification; GET /swap-requests; POST /dispatches/check |
| `dispatch.update` | POST /dispatches/{id}/cancel; POST /dispatches/{id}/swap-requests; POST /swap-requests/{id}/approve; POST /swap-requests/{id}/reject; PUT /dispatches/{id} |
| `driver.create` | POST /drivers |
| `driver.delete` | DELETE /drivers/{id} |
| `driver.read` | GET /devices/{id}/driver-assignments; GET /drivers; GET /drivers/licence-expiries; GET /drivers/{id}; GET /drivers/{id}/assignments |
| `driver.update` | POST /drivers/{id}/assignments; POST /drivers/{id}/assignments/{assignmentId}/end; PUT /drivers/{id} |
| `geofence.create` | POST /geofences |
| `geofence.delete` | DELETE /geofences/{id} |
| `geofence.read` | GET /geofences; GET /geofences/events; GET /geofences/events/summary; GET /geofences/{id}; GET /voices/fence |
| `geofence.update` | PUT /geofences/{id} |
| `group.create` | POST /groups |
| `group.delete` | DELETE /groups/{id} |
| `group.read` | GET /groups; GET /groups/{id} |
| `group.update` | PUT /groups/{id} |
| `maintenance.create` | POST /maintenance-reminders |
| `maintenance.read` | GET /maintenance-reminders; GET /maintenance-reminders/upcoming; GET /maintenance-reminders/{id} |
| `maintenance.update` | POST /maintenance-reminders/{id}/cancel; POST /maintenance-reminders/{id}/complete; PUT /maintenance-reminders/{id} |
| `menu.manage` | DELETE /menus/{id}; GET /menus; GET /menus/{id}; GET /screens; GET /screens/{menuKey}/operations; POST /menus; PUT /menus/{id}; PUT /menus/{id}/operations |
| `own.data.read` | GET /driver/assignment; GET /driver/checklist-template; GET /driver/checklists; GET /driver/dispatches; GET /driver/dispatches/{id}; GET /driver/leave-requests; GET /driver/me; GET /driver/safety-events; GET /driver/safety-score; GET /driver/shifts/current; GET /driver/working-hours; PATCH /driver/me; POST /driver/checklists; POST /driver/dispatches/{id}/accept; POST /driver/dispatches/{id}/complete; POST /driver/dispatches/{id}/decline; POST /driver/dispatches/{id}/start; POST /driver/dispatches/{id}/swap-requests; POST /driver/leave-requests; POST /driver/leave-requests/{id}/cancel; POST /driver/shifts/end; POST /driver/shifts/start |
| `permission.manage` | DELETE /permissions/{code}; GET /permissions; POST /permissions; PUT /permissions/{code} |
| `reference.manage` | PATCH /reference/alarm-types/{id} |
| `renewal.manage` | GET /renewals; POST /renewals |
| `report.read` | GET /reports/driving; GET /reports/export; GET /reports/idle; GET /reports/media; GET /reports/mileage; GET /reports/parking |
| `report.schedule` | DELETE /report-schedules/{id}; GET /report-schedules; GET /report-schedules/{id}; POST /report-schedules; POST /report-schedules/{id}/run; PUT /report-schedules/{id} |
| `role.manage` | DELETE /roles/{id}; POST /roles; PUT /roles/{id} |
| `role.permission.create` | POST /roles/{id}/permissions |
| `role.permission.delete` | DELETE /roles/{id}/permissions |
| `role.permission.read` | GET /permissions; GET /roles/permission-matrix; GET /roles/{id}/menu-permissions; GET /roles/{id}/permissions; GET /screens; GET /screens/{menuKey}/operations |
| `role.permission.update` | PUT /roles/{id}/menu-permissions; PUT /roles/{id}/permissions |
| `role.read` | GET /roles; GET /roles/{id} |
| `sensor.ingest` | GET /sensors/types; POST /devices/{id}/stops/recalculate; POST /sensors/readings |
| `sensor.read` | GET /devices/{deviceId}/sensors/alcohol; GET /devices/{id}/bms; GET /devices/{id}/passenger-summary; GET /devices/{id}/sensors/readings; GET /devices/{id}/stops; GET /devices/{id}/stops/comparison; GET /sensors/types |
| `tenant.all` | DELETE /platform/tenants/{id}; GET /platform/tenants; GET /platform/tenants/{id}; POST /platform/switch-tenant; POST /platform/tenants; PUT /platform/tenants/{id} |
| `track.read` | GET /devices/{id}/track; GET /trips; GET /trips/summary; GET /trips/{id}; GET /trips/{id}/route |
| `trip.create` | POST /trips |
| `trip.delete` | DELETE /trips/{id} |
| `trip.update` | PUT /trips/{id} |
| `user.create` | POST /users |
| `user.delete` | DELETE /users/{id} |
| `user.read` | GET /users; GET /users/tree; GET /users/{id} |
| `user.update` | PATCH /users/{id}/status; POST /users/{id}/password; POST /users/{id}/unlock; PUT /users/{id} |
| `vehicle.create` | POST /vehicles |
| `vehicle.delete` | DELETE /vehicles/{id} |
| `vehicle.read` | GET /vehicles; GET /vehicles/available; GET /vehicles/{id} |
| `vehicle.update` | PUT /vehicles/{id} |
| `vendor.user.create` | POST /vendor-users |
| `vendor.user.delete` | DELETE /vendor-users/{id} |
| `vendor.user.read` | GET /vendor-users; GET /vendor-users/current; GET /vendor-users/{id} |
| `vendor.user.update` | PUT /vendor-users/{id} |
| `video.live` | GET /video/embed; GET /video/sdk-token |
| `video.playback` | GET /devices/{id}/event-markers; GET /devices/{id}/recording-calendar; GET /devices/{id}/recordings; GET /video/embed; GET /video/exports; GET /video/exports/{id}; GET /video/sdk-token; POST /video/exports |
| `voice.create` | POST /voices |
| `voice.read` | GET /voices |
| `workforce.create` | POST /leave-requests |
| `workforce.read` | GET /checklist-template; GET /checklists; GET /drivers/availability; GET /leave-requests; GET /shifts |
| `workforce.update` | POST /leave-requests/{id}/approve; POST /leave-requests/{id}/reject |

`driver.app` is not in the Swagger; it was observed as the `requiredPermissionCode` of every driver menu (live DRIVER login, 2026-10-29).
