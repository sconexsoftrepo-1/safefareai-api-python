---
module: Backend capabilities without a screen (API only) and reference data
user_document: documents/modules/features_not_in_app.md
roles:
- all
permissions: []
apis:
- /api/v1/alarm-rules*
- /api/v1/report-schedules*
- /api/v1/audit-logs
- /api/v1/vendor-users*
- /api/v1/renewals
- /api/v1/voices
- /api/v1/menus*
- /api/v1/screens*
- /api/v1/me/push-tokens
- /api/v1/reference/*
sources:
- provided Swagger
- docs/v10-api-frontend-mapping.md
- docs/evidence/final-frontend-gap-audit.md
status: NOT IMPLEMENTED IN FRONTEND — exist in provided Swagger only (except reference reads, which screens use)
---

# Features not in the app — backend endpoints

Technical companion of `documents/modules/features_not_in_app.md`.

Iris must **not** give screen instructions for these — there is no screen. It may explain that the capability exists in the backend but isn't available in the app yet.

| Capability | Endpoints | Permission | Notes |
|---|---|---|---|
| Alarm rules (how each alarm type is handled: HIDE, DISPLAY_ONLY, PROCESS, HIGH_PRIORITY; AUTO/MANUAL) | `GET/POST /alarm-rules`, `GET/PUT/DELETE /alarm-rules/{id}` | alarm.rule.read/create/update/delete | no UI |
| Report schedules (PARKING, DRIVING, MILEAGE, MEDIA, ALARMS, TRIPS, IDLE as CSV/XLSX/PDF) | `/report-schedules*`, `POST /report-schedules/{id}/run` | report.schedule | no UI |
| Report export / idle report | `GET /reports/export`, `GET /reports/idle` | report.read | no UI |
| Audit log | `GET /audit-logs` | audit.read | no UI |
| Vendor (GPSTrackTech) user accounts | `/vendor-users*` | vendor.user.* | deliberately deferred (vendor side effects) |
| Renewals (device service renewal, consumes vendor coins) | `GET/POST /renewals` | renewal.manage | deliberately deferred |
| Voice files | `GET/POST /voices` | voice.read / voice.create | only `GET /voices/fence` shown read-only on Geofences |
| Menu administration and screen operations | `/menus*`, `PUT /menus/{id}/operations`, `GET /screens*`, `/roles/{id}/menu-permissions` | menu.manage / role.permission.* | no UI |
| Push tokens (mobile push) | `GET/POST/DELETE /me/push-tokens` | signed in | no UI |
| Alarm type configuration | `PATCH /reference/alarm-types/{id}` | reference.manage | no UI |
| Device transfer / delete | `POST /devices/transfer`, `DELETE /devices/{id}` | device.update / device.delete | buttons disabled |
| Trip create/edit/delete | `POST /trips`, `PUT/DELETE /trips/{id}` | trip.* | no UI |
| User delete | `DELETE /users/{id}` | user.delete | not exposed |
| Tenant edit/delete | `GET/PUT/DELETE /platform/tenants/{id}` | tenant.all | no UI |
| Video live/embed/SDK token | `GET /video/embed`, `GET /video/sdk-token` | video.live / video.playback | unused |
| Fleet health, heatmap, false positives | `GET /dashboard/fleet-health`, `/safety/heatmap`, `/safety/false-positives` | device.read / alarm.read | unused |
| Asset tree | `GET /assets/tree` | device.read | unused (tree built client-side) |
| Device diagnostics | `GET /devices/{id}/passthrough-data` | device.read | `type` code undocumented |
