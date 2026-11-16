---
title: Module index
category: modules
---

# Module index

Status legend: **VERIFIED LIVE** (seen working against the live server) · **IMPLEMENTED, NOT VERIFIED** · **PARTIALLY IMPLEMENTED** · **NOT IMPLEMENTED IN FRONTEND** (no screen).

| # | Module | Document | Screen permission | Status |
|---|---|---|---|---|
| 1 | Authentication / sign-in | modules/authentication_login.md | public | VERIFIED LIVE |
| 2 | App shell & navigation | modules/app_shell_navigation.md | — | VERIFIED LIVE (Admin, Driver) |
| 3 | Dashboard — Fleet Overview | modules/dashboard_overview.md | device.read | VERIFIED LIVE (read) |
| 4 | Platform Overview | modules/platform_overview.md | tenant.all + platform | IMPLEMENTED, NOT VERIFIED here |
| 5 | Organizations / Tenants | modules/tenants_organizations.md | tenant.all + platform | IMPLEMENTED; create NOT VERIFIED |
| 6 | Live Monitoring | modules/live_monitoring.md | device.read | VERIFIED LIVE |
| 7 | Historical Video | modules/historical_video.md | video.playback | PARTIALLY IMPLEMENTED (no playback) |
| 8 | Trips & Tracking | modules/trips_tracking.md | track.read | VERIFIED LIVE (read-only) |
| 9 | Reports | modules/reports.md | report.read | VERIFIED LIVE; no download |
| 10 | Vehicles (registry) | modules/vehicle_registry.md | vehicle.read | IMPLEMENTED, NOT VERIFIED |
| 11 | Devices (Vehicles & Assets) | modules/devices_vehicles_assets.md | device.read | Read VERIFIED; create/edit NOT VERIFIED; transfer/delete disabled |
| 12 | Device Groups | modules/device_groups.md | group.read | Read-only |
| 13 | Sensors | modules/sensors_passenger_counting.md | sensor.read | IMPLEMENTED, NOT VERIFIED |
| 14 | Drivers | modules/drivers.md | driver.read | Read VERIFIED; writes NOT VERIFIED |
| 15 | Driver Assignments | modules/driver_assignments.md | driver.update | Read VERIFIED; writes NOT VERIFIED |
| 16 | Dispatch | modules/dispatch.md | dispatch.read | Read VERIFIED (empty); writes NOT VERIFIED |
| 17 | Workforce — availability, shifts, checklists | modules/workforce_shifts.md | workforce.read | VERIFIED LIVE (read) |
| 18 | Leave Management | modules/leave_management.md | workforce.read | Read VERIFIED; writes NOT VERIFIED |
| 19 | Alerts & Events — Incidents | modules/alerts_incidents.md | alarm.read | Read VERIFIED; actions NOT VERIFIED; assign NOT AVAILABLE |
| 20 | AI Alarms | modules/ai_alarms.md | alarm.read | VERIFIED LIVE |
| 21 | Routine Alarms | modules/routine_alarms.md | alarm.read | VERIFIED LIVE |
| 22 | Safety Analytics | modules/safety_analytics.md | alarm.read | VERIFIED LIVE (read) |
| 23 | Safety Scores | modules/safety_scores.md | alarm.read | VERIFIED LIVE (read) |
| 24 | Geofences | modules/geofences.md | geofence.read | Read VERIFIED; create/edit NOT IMPLEMENTED |
| 25 | Notifications | modules/notifications.md | signed in | Read VERIFIED (empty) |
| 26 | Global Search | modules/global_search.md | device.read for records | VERIFIED LIVE |
| 27 | Device Commands | modules/device_commands.md | command.send | Read-only; detail blocked; send disabled |
| 28 | Users & Sub-Accounts | modules/users_sub_accounts.md | user.read | Read VERIFIED; writes NOT VERIFIED; delete missing |
| 29 | Roles & Permissions admin | modules/roles_permissions_admin.md | role.read / permission.manage + platform | IMPLEMENTED, NOT VERIFIED here |
| 30 | Settings | modules/settings.md | signed in (non-driver) | VERIFIED LIVE (profile, prefs) |
| 31 | Maintenance | modules/maintenance.md | maintenance.read | NOT IMPLEMENTED IN FRONTEND (reminders from device dates only) |
| 32 | Driver app — My Work | modules/driver_my_work.md | driver.app + own.data.read | Read VERIFIED (Driver); writes NOT VERIFIED |
| 33 | Iris AI / Assistant | modules/iris_assistant.md | device.read | Prompts VERIFIED; ask NOT VERIFIED |
| 34 | Features not available in the app | modules/features_not_in_app.md | — | NOT IMPLEMENTED IN FRONTEND |

**Requested modules that don't exist as separate screens:** Shifts (part of Workforce), Leave (Workforce tab / My Leave), Driver Assignments (Drivers), Device Groups (Vehicles & Assets), Safety Scores (Safety Analytics), Search (header), Notifications (header), Maintenance (no screen), Driver Mobile App (web My Work; no native app in the project).

Technical details (APIs, payloads, source files) for every module are kept separately in `../api/modules/<module>_api.md`.
