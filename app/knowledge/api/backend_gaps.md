---
title: Backend gaps, open questions and frontend/backend inconsistencies
category: api
sources: [docs/missing-backend-apis.md, docs/evidence/final-frontend-gap-audit.md, docs/feature-status.md, source inspection 2026-11-05]
---

# Backend gaps and inconsistencies (technical)

Ids like #13 refer to `docs/missing-backend-apis.md`; GA-xx to `docs/evidence/final-frontend-gap-audit.md` in the frontend ZIP.

## A. Missing features — technical reasons
| Feature | Situation |
|---|---|
| Historical video playback | Vendor SDK/player not provided (GA-08). Export only. |
| Report download / export, report schedules | No UI; `GET /reports/export`, `/report-schedules*` exist in Swagger (GA-17). |
| Device transfer, device delete, create/edit groups | Buttons disabled pending backend confirmation (charges, side effects). |
| Fit/unlink a device in a vehicle | `vehicleId`/`unlinkVehicle` supported by API, not by the device forms. |
| Bus passenger capacity on vehicles | `passengerCapacity` in API, not in the vehicle form (default 44). |
| Geofence create/edit | Rule/area/colour codes undocumented (Q2). |
| Send device command | Disabled (execution contract undocumented, #25). |
| Assign alert to a person | Swagger body wrong (#32). |
| Delete user, edit roles from Users screen | Not exposed (#24); roles edited only by Safe-Fare Admin in Global Roles. |
| Maintenance reminders management, alarm rules, audit log, vendor users, renewals, voice upload, menu admin, push tokens | API only (`api_only_capabilities.md`). |
| Forgot password | Not in frontend or Swagger. |
| Native driver mobile app | Not in the project; My Work is the web driver app. |
| Online/offline filter on Live Monitoring | Not present (Overview link `?status=offline` is ignored). |
| Notification push/polling | Not implemented (GA-20). |

## B. Backend items awaiting confirmation (from the frontend team)
- Fleet Owner role code (MANAGER?) and permission set; Fleet Owner data isolation (GA-02 blocked).
- Status/transition tables for dispatch, leave, alerts (partly in Swagger enums now); severity scale; `statusCode`, `positionMode`, `networkType` meanings.
- Video export cost, status values, placeholder URLs (#29, #34).
- Recording calendar `month` format (#21).
- Write-test prerequisites (#37): no write flow has been verified live.
- `GET /commands/{id}` → 500 (#28); unknown driver `/safety-events` → 200 empty (#35); alert status vs history (#36); geofence freshness metadata (#30).

## C. Frontend/backend and documentation inconsistencies found in this audit
1. Repo Swagger snapshot `docs/openapi/api-docs-v10.json` (220 ops) is older than the provided Swagger (242 ops): vehicles, sensors, alcohol, tenants CRUD, notifications poll and role menu-permissions are "off-spec" in the frontend code but are present in the provided Swagger.
2. Fleet Overview "Offline" tile → `/drive-vision/monitoring?status=offline`, but Live Monitoring doesn't read `status`.
3. Vehicle Registry delete hint tells users to unlink the device via device edit, which has no unlink field.
4. Menu naming: **Vehicles** = vehicle registry; **Vehicles & Assets** = devices; the device create button is labelled **Add vehicle**.
5. README.md describes the old sample-data demo (simulated monitoring, local preferences, rule-based assistant) — outdated; the code now uses the BFF.
6. `docs/evidence/final-frontend-gap-audit.md` §1 says ADMIN/MANAGER see "No access"; the newer V10 permission-based policy (2026-11-02) grants screens by permission codes.
7. `driver.app` permission is required by the frontend but not in Swagger (observed in `/me/menus`).
8. `AssignRequest` is shared by driver assignment and alert assignment in Swagger (#32).
9. Notifications unread-count response keys undocumented (observed `{unread}`).
10. The Java `assistant-controller` overlaps with the new Iris AI service.

## D. Data caveat
Live verification used a dev tenant with 0–1 rows per list; non-empty data behaviour of many screens is NOT VERIFIED.
