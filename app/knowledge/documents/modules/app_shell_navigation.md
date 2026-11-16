---
module: App shell and navigation
feature_keys:
- sidebar
- topbar
- breadcrumbs
- mobile-nav
- section-switcher
- page-not-found
routes:
- /drive-vision/*
roles:
- all signed-in users
permissions:
- screen-level codes; see roles_permissions.md
availability: VERIFIED LIVE (Admin, Driver)
technical_reference: api/modules/app_shell_navigation_api.md
---

# App shell and navigation

## 1. Purpose
The frame around every screen: left sidebar menu, top bar (search, tenant switcher, notifications bell, Iris launcher, profile menu), breadcrumbs, mobile drawer, and the "page not found / no access" panels.

## 2. Exact sidebar menu (in order)
| Group | Menu label | Opens with permission |
|---|---|---|
| My work | My Work | `own.data.read` + `driver.app` (driver logins only) |
| Platform | Platform Overview | Safe-Fare Admin + `tenant.all` |
| Platform | Tenants | Safe-Fare Admin + `tenant.all` |
| Platform | Global Roles | Safe-Fare Admin + `role.read` |
| Platform | Permission Catalogue | Safe-Fare Admin + `permission.manage` |
| Overview | Fleet Overview | `device.read` |
| Monitor | Live Monitoring | `device.read` |
| Monitor | Historical Video | `video.playback` |
| Monitor | Trips & Tracking | `track.read` |
| Monitor | Reports | `report.read` |
| Monitor | Vehicles | `vehicle.read` |
| Monitor | Sensors | `sensor.read` |
| Fleet | Vehicles & Assets | `device.read` |
| Fleet | Drivers | `driver.read` |
| Fleet | Dispatch | `dispatch.read` |
| Fleet | Workforce | `workforce.read` |
| Safety | Alerts & Events | `alarm.read` |
| Safety | Safety Analytics | `alarm.read` |
| Manage | Geofences | `geofence.read` |
| Manage | Device Commands | `command.send` |
| Administration | Users & Sub-Accounts | `user.read` |
| Administration | Settings | any signed-in non-driver user |

Menu items a user can't open are hidden. For driver logins the menu titles and order come from the server and lead to the My Work pages.

> Note the two similarly named menus: **Vehicles** is the vehicle registry (number plate, make, model); **Vehicles & Assets** is the list of tracking **devices** and groups.

## 3. Screens
- Sidebar (collapsible: **Expand navigation** / **Collapse**), mobile drawer on small screens.
- Top bar: page title + subtitle, global search (**Ctrl K**), tenant switcher (Safe-Fare Admin only), notification bell, Iris launcher (users with `device.read`), profile menu.
- Fleet Overview's title is a greeting: "Good morning/afternoon/evening, <name>" (fleet time IST).
- Access panels: "You don't have access to this page", "No access for this account yet", "Page not found".

## 4–8.
Navigation only; no forms or tables.

## 9. Workflows
- **Find a page**: use the sidebar, or press **Ctrl K** and type the page name (see `global_search.md`).
- **On a phone**: open the menu icon to show the navigation drawer.

## 10–11. Roles and permissions
See table above and `roles_permissions.md`. Rule: the frontend is deny-by-default and the server still authorises every request.

## 16. Business rules
- Server `screens` can only narrow access (read-only screens hide write buttons; `allowed:false` removes actions). They never open a screen the permissions don't.

## 17. Errors
- An unknown page address shows "Page not found" inside the app.
- If the driver menu can't be loaded, the sidebar shows a single "My Work" entry (no error message is shown) — PARTIALLY IMPLEMENTED.

## 18. Common questions
- **Why can't I see a menu?** Your permissions don't include that screen's code (table above). Ask an administrator to add it to your role.
- **What's the difference between Vehicles and Vehicles & Assets?** Vehicles = registered vehicles (number, make, model, which device is fitted). Vehicles & Assets = tracking devices, their groups and live state.
- **Where is Maintenance / Alarm rules / Audit log?** There is no screen for them in this app (APIs exist only; see `features_not_in_app.md`).

## 19. Limitations
- Notifications and leave links for drivers were fixed to point to driver pages; footer link "Open Alerts & Events" in the bell is for fleet users.
