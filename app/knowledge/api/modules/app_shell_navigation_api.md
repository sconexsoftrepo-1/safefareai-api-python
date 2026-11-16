---
module: App shell and navigation
user_document: documents/modules/app_shell_navigation.md
roles:
- all signed-in users
permissions:
- screen-level codes; see roles_permissions.md
apis:
- GET /api/v1/me/permissions
- GET /api/v1/me/menus
sources:
- src/components/drive-vision/navigation/nav-config.ts
- src/components/drive-vision/navigation/use-nav.ts
- src/components/drive-vision/app-shell/sidebar.tsx
- src/components/drive-vision/app-shell/topbar.tsx
- src/components/drive-vision/app-shell/mobile-nav.tsx
- src/components/drive-vision/app-shell/breadcrumbs.tsx
- src/app/drive-vision/layout.tsx
- src/app/drive-vision/not-found.tsx
- src/app/drive-vision/[...slug]/page.tsx
status: VERIFIED LIVE for Admin and Driver navigation (docs/evidence/phase1b-admin-access.md, docs/feature-status.md)
---

# App shell and navigation — API and implementation reference

Technical companion of `documents/modules/app_shell_navigation.md`. For the Iris tool layer and developers; not for quoting to end users.

## 12. Files
See front matter.
## 13. APIs
`GET /me/permissions` (identity, permissions, `screens[]` with `routePath`, `readOnly`, `operations[].allowed`) and `GET /me/menus` (`MenuNodeDto {menuKey, title, routeKey, routePath, requiredPermissionCode, sortOrder, visible, active, children}`).

## Technical details referenced by the user document

| My work | My Work | `/drive-vision/my-work` | `own.data.read` + `driver.app` (driver logins only) |
| Platform | Platform Overview | `/drive-vision/platform` | Safe-Fare Admin (`platform=true`) + `tenant.all` |
| Platform | Tenants | `/drive-vision/tenants` | Safe-Fare Admin + `tenant.all` |
| Platform | Global Roles | `/drive-vision/platform/roles` | Safe-Fare Admin + `role.read` |
| Platform | Permission Catalogue | `/drive-vision/platform/permissions` | Safe-Fare Admin + `permission.manage` |
| Overview | Fleet Overview | `/drive-vision/overview` | `device.read` |
| Monitor | Live Monitoring | `/drive-vision/monitoring` | `device.read` |
| Monitor | Historical Video | `/drive-vision/video` | `video.playback` |
| Monitor | Trips & Tracking | `/drive-vision/trips` | `track.read` |
| Monitor | Reports | `/drive-vision/reports` | `report.read` |
| Monitor | Vehicles | `/drive-vision/vehicle-registry` | `vehicle.read` |
| Monitor | Sensors | `/drive-vision/sensors` | `sensor.read` |
| Fleet | Vehicles & Assets | `/drive-vision/vehicles` | `device.read` |
| Fleet | Drivers | `/drive-vision/drivers` | `driver.read` |
| Fleet | Dispatch | `/drive-vision/dispatch` | `dispatch.read` |
| Fleet | Workforce | `/drive-vision/workforce` | `workforce.read` |
| Safety | Alerts & Events | `/drive-vision/alerts` | `alarm.read` |
| Safety | Safety Analytics | `/drive-vision/safety` | `alarm.read` |
| Manage | Geofences | `/drive-vision/geofences` | `geofence.read` |
| Manage | Device Commands | `/drive-vision/devices/commands` | `command.send` |
| Administration | Users & Sub-Accounts | `/drive-vision/users` | `user.read` |
| Administration | Settings | `/drive-vision/settings` | any signed-in non-driver user |
- Menu items a user can't open are hidden. For driver logins the sidebar is built from the server's `GET /me/menus` (titles and order), mapped to My Work sub-pages.
- > Note the two similarly named menus: **Vehicles** (`/vehicle-registry`) is the vehicle registry (number plate, make, model); **Vehicles & Assets** (`/vehicles`) is the list of tracking **devices** and groups.
- Known server `routePath` → app route mappings: `/dashboard`→Fleet Overview, `/alarms`→Alerts & Events, `/reports`→Reports, `/vehicle-registry`→Vehicles, `/sensors`→Sensors, `/tenants`→Tenants, `/platform/roles`→Global Roles, `/platform/permissions`→Permission Catalogue, `/driver/work|shifts|leave|checklist|safety|profile`→My Work pages, `/driver/notifications`→no page (bell). Any other routePath is ignored.
- Unknown `/drive-vision/...` URL → in-shell "Page not found" (HTTP 200 soft 404).
- `/me/menus` failure for a driver → sidebar falls back to a single "My Work" entry (direct URLs still work) — PARTIALLY IMPLEMENTED (GA-14: error not displayed).
- The server `menuKey` catalogue is undocumented, so `menuKey` isn't used for routing.
