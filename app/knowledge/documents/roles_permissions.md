---
title: Roles and permissions
category: roles_permissions
---

# Roles and permissions

## 1. How access works
- **Permissions decide everything.** Each screen, widget and button opens only if the user's permission set contains the exact code(s) below. A role code never grants access by itself; it can only narrow (e.g. the driver app is only for DRIVER logins).
- **The server checks every request.** Even if a button were shown, the SafeFare server refuses actions the user isn't allowed to do, and records of other organisations are reported as not found.
- **Platform vs tenant.** `platform === true` marks the **Safe-Fare Admin** (platform administrator, signs in without a tenant code). Everyone else is a **tenant user** whose tenant comes from their token.
- **Server screen settings** can make a screen read-only or hide an action; they never open extra screens.

## 2. The product roles (and what the backend actually has)
| Product role | Backend evidence | Notes |
|---|---|---|
| **Admin — Safe-Fare Admin (platform)** | `platform: true`, role code `ADMIN` (V10 merged PLATFORM_ADMIN/SUPER_ADMIN into ADMIN), holds all codes incl. `tenant.all` | Sees platform screens, works in "All tenants" mode or a selected tenant. |
| **Admin — tenant ADMIN** | `platform: false`, role `ADMIN` ("Full tenant administration"), every code except `tenant.all` | Full tenant administration; no platform screens. |
| **Fleet Owner** | **NOT CONFIRMED.** The backend has roles `MANAGER` ("Fleet manager") and `OPERATOR` ("Operations user"), but has not confirmed which one is "Fleet Owner" | Access follows whatever permissions the role holds. Synthetic test fixture: device.read, group.read, track.read, alarm.read, report.read, driver.read/create/update, dispatch.read/create/update, workforce.read/create/update. |
| **Driver** | Role `DRIVER`, permissions `driver.app` + `own.data.read` (observed live 2026-10-29) | My Work only; must be linked to a driver profile. |

## 3. Screen → permission
| Screen | Permission | Audience |
|---|---|---|
| Platform Overview | tenant.all + platform | Safe-Fare Admin |
| Tenants | tenant.all + platform | Safe-Fare Admin |
| Global Roles | role.read + platform | Safe-Fare Admin |
| Permission Catalogue | permission.manage + platform | Safe-Fare Admin |
| Fleet Overview | device.read | fleet users |
| Live Monitoring | device.read | fleet users |
| Historical Video | video.playback | fleet users |
| Trips & Tracking | track.read | fleet users |
| Reports | report.read | fleet users |
| Vehicles (registry) | vehicle.read | fleet users |
| Sensors | sensor.read | fleet users |
| Vehicles & Assets (devices) | device.read | fleet users |
| Drivers | driver.read | fleet users |
| Dispatch | dispatch.read | fleet users |
| Workforce | workforce.read | fleet users |
| Alerts & Events | alarm.read | fleet users |
| Safety Analytics | alarm.read | fleet users |
| Geofences | geofence.read | fleet users |
| Device Commands | command.send | fleet users |
| Users & Sub-Accounts | user.read | fleet users |
| Settings | any signed-in user | not drivers |
| My Work (6 pages) | own.data.read + driver.app | DRIVER logins only |
| Iris assistant (header) | — | device.read | fleet users |
| Record search (header) | — | device.read | fleet users |

## 4. Actions → permission (buttons)
| Action | Permission | Tenant needed (Safe-Fare Admin)? |
|---|---|---|
| Create / edit / delete driver; assign or end assignment | driver.create / driver.update / driver.delete | yes |
| Create dispatch / edit, cancel, request swap / approve-reject swap | dispatch.create / dispatch.update | yes |
| Request leave for a driver / approve-reject leave | workforce.create / workforce.update | yes |
| Acknowledge, comment, resolve, dismiss, reopen alert | alarm.handle | yes |
| Delete geofence | geofence.delete | yes |
| Request video export | video.playback | yes |
| Create / edit, enable-disable, unlock, reset password of user | user.create / user.update | yes |
| Register / edit device | device.create / device.update | yes |
| Register / edit / delete vehicle | vehicle.create / vehicle.update / vehicle.delete | yes |
| Add sensor reading / recalculate stops | sensor.ingest | yes |
| Own profile & preferences, own password, notification read state | signed in | no |
| Driver self-service actions | own.data.read | no |
| Global roles, role permissions, permission catalogue | role.manage, role.permission.create/delete/update, permission.manage (+platform) | no |
| Create tenant | tenant.all (+platform) | no |

## 5. Data isolation rules
- Every record is scoped to the caller's tenant; another tenant's record answers **404**, asking for another organisation is refused (TENANT_ACCESS_DENIED).
- Safe-Fare Admin reads without a tenant cover every tenant; creating or changing records without one is refused (TENANT_REQUIRED).
- Driver logins must be linked to a driver profile and only ever get that driver's own data; the server refuses driver logins on fleet data (verified 2026-10-31).
- Fleet Owner isolation inside a tenant (e.g. by group) is **NOT VERIFIED** (no test accounts were available).

## 6. Common questions
- **Why can't I access a menu?** Your permissions don't include the code in §3; an admin must add it to your role (Safe-Fare Admin: Global Roles / Permission Catalogue).
- **Why can't a driver access the admin dashboard?** Drivers have only `driver.app` + `own.data.read`; Fleet Overview needs `device.read`.
- **Why are create buttons missing for the Safe-Fare Admin?** No tenant selected ("All tenants" mode).
