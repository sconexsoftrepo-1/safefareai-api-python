---
module: Dashboard / Fleet Overview
feature_keys:
- dashboard
- overview
- kpis
- online-offline
- device-health
- trends
- reminders
- fleet-groups
routes:
- /drive-vision/overview
roles:
- Safe-Fare Admin
- Tenant ADMIN
- Fleet Owner
- any user with device.read
permissions:
- device.read (screen)
- alarm.read (safety widget)
- group.read (groups widget)
availability: VERIFIED LIVE (read)
technical_reference: api/modules/dashboard_overview_api.md
---

# Dashboard — Fleet Overview

## 1. Purpose
The home screen for fleet users: fleet size, how many devices are online/offline, device health, safety events, today's trips and dispatches, pending workforce items, reminders and quick links — for the selected date range.

## 2. Navigation
Sidebar **Overview → Fleet Overview**. The page title is a greeting ("Good morning, <name>"); subtitle "Fleet activity, safety and upcoming work at a glance".

## 3. Screen sections
1. **Date range** selector: Today · Last 7 days (default) · Last 30 days; **Refresh** button ("Refresh dashboard data").
2. **Key metrics** row: Total devices, Online, Offline, Expiring (service ≤ 30 days), Moving now, Distance today.
3. **Fleet status** card: *Vehicle status breakdown* (server `fleet-status` slices) and *Device health* (Online, Offline, Never online, Service expired, Stale > 24 h, Low battery, …).
4. **Device connectivity and service** / **GPS freshness** ("Devices reporting within the last hour", Stale GPS > 1 h, No GPS fix).
5. **Fleet activity / Analytics**: alarm and AI-event trend chart ("AI events (ADAS · DSM · BSD)" vs "Routine alarms").
6. **Today's operations**: Trips in progress, Trips today, Dispatches today, Licences expiring, Pending leave, Pending swaps, On leave today.
7. **Daily trend** (**Show as table**: Day, Distance, Alarms, Severe).
8. **Upcoming reminders** (service expiry, insurance due, maintenance due from device records).
9. **Fleet groups** (device count and events per group; needs `group.read`).
10. **Recent activity** and **Quick links** (Live Monitoring, Vehicles, Historical Video, Trips, Alerts).

## 4. Metric definitions (what each number means)
| Metric | Definition |
|---|---|
| Total devices | Number of tracking devices the user can see. |
| Online / Offline | **Server counts** of devices currently reporting / not reporting. The app never decides online/offline itself. |
| Expiring | Devices whose service expiry is within 30 days. |
| Moving now | Devices moving (speed above 0) with a report no older than 5 minutes. |
| Stale GPS > 1 h | No report time, or last report older than 1 hour. |
| Low battery | Battery below 20 % (key metrics), or the server's own threshold on the health card. |
| Stale > 24 h | Server count: no report for over 24 hours. |
| Never online, Service expired, Video capable, Insurance/Maintenance due 30 d | Server counts. |
| Vehicles total/online/offline/driving/idling/parked | Server counts. |
| Trips in progress, trips today, distance today, dispatches today (by status) | Server counts. |
| Open / severe alerts, AI vs routine, by severity | Server counts for the range. |
| Pending leave, pending swaps, on leave today, active drivers, licences expiring 30 d, unread notifications | Server counts. |
Missing values are shown as "—", never as 0.

## 5. Buttons
Date range selector; **Refresh**; **Retry** on any failed widget; metric tiles link to related screens (e.g. Offline opens Live Monitoring — note the list there is not filtered to offline devices); quick-link tiles; **Show as table** on the trend.

## 6–8. Forms, tables, paging
No forms. Daily-trend table (Day, Distance, Alarms, Severe). Ranking widget metric: Mileage / Driving time.

## 9. Workflows
**Check how many devices are online/offline**: open Fleet Overview → read Online / Offline tiles (server counts) → select Offline to open Live Monitoring.
**See today's alarms**: set Date range = Today → Fleet activity chart and Alerts & AI events; select Alerts quick link for the list.

## 10–11. Roles and permissions
Screen: `device.read`. Safety widget: `alarm.read`. Groups widget: `group.read`. A widget without its permission shows "No permission for this widget". Drivers don't see this screen.

## 16. Business rules
- Fleet time zone is IST (Asia/Kolkata) for "today" and greetings.
- Undocumented device codes and the severity scale are shown as received, never interpreted.
- For the Safe-Fare Admin in "All tenants" mode, figures cover every tenant.

## 17. Error handling
Each widget fails independently with "Couldn't load …" + **Retry**; 503 from alarms shows "AI events unavailable" / "Routine alarms unavailable" rather than zero.

## 18. Common questions
- **What does online/offline mean?** Online = the device is currently reporting to the GPS vendor; offline = it isn't. Both numbers are counts calculated by the SafeFare server.
- **What is "Stale > 24 h"?** Devices whose last report is more than 24 hours old (server count).
- **Why is a number shown as "—"?** The server didn't return it or the request failed; the app never substitutes 0.
- **Why does the dashboard not load?** You need `device.read`; otherwise check the per-widget error (network, 401 session expired, 503 vendor unavailable).
- **Where do I see pending leave and pending swaps?** Fleet Overview → *Today's operations* shows Pending leave, Pending swaps, On leave today and Licences expiring (server counts). Details: Workforce → Leave and Dispatch → Swap requests.

## 19. Limitations
- The page loads a lot of data at once, so it can be slow for large fleets.
- Data on the dev tenant was a small demo set (0–1 rows) during verification.
