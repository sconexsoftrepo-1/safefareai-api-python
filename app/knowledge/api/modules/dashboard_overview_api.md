---
module: Dashboard / Fleet Overview
user_document: documents/modules/dashboard_overview.md
roles:
- Safe-Fare Admin
- Tenant ADMIN
- Fleet Owner
- any user with device.read
permissions:
- device.read (screen)
- alarm.read (safety widget)
- group.read (groups widget)
apis:
- GET /api/v1/dashboard/overview
- GET /api/v1/dashboard/fleet-status
- GET /api/v1/dashboard/trends
- GET /api/v1/dashboard/safety-events
- GET /api/v1/monitor/realtime
- GET /api/v1/devices
- GET /api/v1/groups
- GET /api/v1/alarms/ai
- GET /api/v1/alarms/routine
- GET /api/v1/me/preferences
sources:
- src/app/drive-vision/overview/page.tsx
- src/components/drive-vision/dashboard/fleet-overview.tsx
- src/components/drive-vision/dashboard/live-dashboard-model.ts
- src/components/drive-vision/dashboard/dashboard-api-model.ts
- src/components/drive-vision/dashboard/operations-panels.tsx
- src/components/drive-vision/dashboard/fleet-status-card.tsx
- src/components/drive-vision/dashboard/alarm-trend-chart.tsx
- src/components/drive-vision/dashboard/fleet-groups.tsx
- src/components/drive-vision/dashboard/reminders-list.tsx
- src/components/drive-vision/dashboard/usage-ranking.tsx
- src/components/drive-vision/dashboard/activity-feed.tsx
- src/features/drive-vision/api/insight-service.ts
server_route_paths:
- /dashboard
status: VERIFIED LIVE (read) 2026-10-29 with small demo data (docs/feature-status.md)
---

# Dashboard / Fleet Overview — API and implementation reference

Technical companion of `documents/modules/dashboard_overview.md`. For the Iris tool layer and developers; not for quoting to end users.

## 13–15. APIs and responses
- `GET /dashboard/overview` → `OverviewDto {generatedAt, vehicles: VehicleCounts, trips: ActiveTrips, safety: SafetySummary, health: DeviceHealth, operations: Operations}`.
- `GET /dashboard/fleet-status` → `[StatusSlice {status, label, count, percent}]`.
- `GET /dashboard/trends?from&to` → `[TrendDay]`.
- `GET /dashboard/safety-events?from&to` → `SafetySummary {from, to, total, open, severe, ai, routine, bySeverity, latestOpen[AlertRow]}`.
- `GET /monitor/realtime` → `RealtimeDto {onlineCount, offlineCount, devices[DeviceStateDto]}`.
Vendor-backed responses carry `extend.source/stale/fallbackReason`.

## Technical details referenced by the user document

- Sidebar **Overview → Fleet Overview** (`/drive-vision/overview`). The page title is a greeting ("Good morning, <name>"); subtitle "Fleet activity, safety and upcoming work at a glance". Server menu routePath `/dashboard` maps here.
- 7. **Daily trend** (server `/dashboard/trends`; **Show as table**: Day, Distance, Alarms, Severe).
| Total devices | `GET /devices` (all pages) | Number of tracking devices the user can see. |
| Online / Offline | `GET /monitor/realtime` → `onlineCount` / `offlineCount` | **Server counts** of devices currently reporting / not reporting. The app never decides online/offline itself. |
| Expiring | DeviceDto `expiresAt` | Devices whose service expiry is within 30 days (`EXPIRING_DAYS`). |
| Stale GPS > 1 h | realtime `deviceTime` | No report time, or last report older than 1 hour. |
| Low battery | realtime `batteryPct < 20` (client) / server `lowBattery` count | Battery below 20 % (client), or the server's own threshold for the health card. |
| Stale > 24 h | `/dashboard/overview` health `staleOver24h` | Server count: no report for over 24 hours. |
| Never online, Service expired, Video capable, Insurance/Maintenance due 30 d | `DeviceHealth` from `/dashboard/overview` | Server counts. |
| Vehicles total/online/offline/driving/idling/parked | `VehicleCounts` from `/dashboard/overview` | Server counts. |
| Open / severe alerts, AI vs routine, by severity | `SafetySummary` (`/dashboard/safety-events?from&to`) | Server counts for the range. |
- Date range selector; **Refresh**; **Retry** on any failed widget; metric tiles link to related screens (e.g. Offline → `/drive-vision/monitoring?status=offline`; note: Live Monitoring ignores `status`, so the list is not filtered); quick-link tiles; **Show as table** on the trend.
- Undocumented codes (`statusCode`, `positionMode`, severity scale) are never interpreted.
- **What does online/offline mean?** Online = the device is currently reporting to the GPS vendor; offline = it isn't. Both numbers are the server's counts from `/monitor/realtime`.
- `GET /dashboard/vehicles`, `/active-trips`, `/device-health` are not called separately (overview already contains them); `/dashboard/fleet-health` is unused.
- Heavy request fan-out (devices, groups, realtime, alarms paged) — GA-22.
