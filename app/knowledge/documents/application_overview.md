---
title: SafeFare application overview
category: overview
---

# What is SafeFare?

**SafeFare AI** ("Smarter Fleet. Safer Journey.") is an AI-powered **fleet management and driver-safety** application. Fleet operators use it to track vehicles live on a map, review camera-based AI safety events and alarms, manage vehicles, tracking devices, drivers, dispatches, shifts and leave, and analyse safety and mileage. Drivers use its **My Work** section to see their trips, shifts, leave, checklist and safety score.

- **Web app:** "SafeFare AI — Fleet Management UI" (formerly "Drive Vision"), used in the browser on desktop, tablet and phone.
- **SafeFare server:** stores the organisation's data and connects to the GPS/video provider **GPSTrackTech**, which supplies device positions, alarms and video.
- **Organisations:** multi-tenant. Each organisation (tenant) sees only its own data; the Safe-Fare Admin manages all tenants.

## Who uses it
| User | Typical work |
|---|---|
| Safe-Fare Admin (platform) | Tenants, global roles and permissions, platform-wide view |
| Tenant admin / Fleet owner / fleet manager | Dashboard, live monitoring, alerts, vehicles, devices, drivers, dispatch, workforce, reports, users |
| Driver | My Work: trips, shifts, leave, checklist, safety, profile |

## Main modules (menu → purpose)
| Menu | Purpose |
|---|---|
| Fleet Overview | Dashboard KPIs: devices online/offline, health, safety events, today's operations, reminders |
| Live Monitoring | Live map of vehicle positions and live camera |
| Historical Video | Recording calendar, recordings, clip exports (playback not yet available) |
| Trips & Tracking | Trip history, route and GPS track playback |
| Reports | Mileage, driving, parking, media reports |
| Vehicles | Vehicle registry (number, make, model, fitted device) |
| Sensors | Bus passenger counts (IR vs BMS), capacity, alcohol check |
| Vehicles & Assets | Tracking devices and groups |
| Drivers | Driver records, licences, assignments, safety score |
| Dispatch | Planned trips for drivers, conflicts, swaps |
| Workforce | Availability, shifts, leave, checklists |
| Alerts & Events | Incidents handling, AI events, routine alarms |
| Safety Analytics | Safety trends and scores |
| Geofences | Zones/route lines, geofence events |
| Device Commands | Command history (sending disabled) |
| Users & Sub-Accounts | Login accounts and hierarchy |
| Settings | Profile, password, preferences |
| Platform (Admin) | Platform Overview, Tenants, Global Roles, Permission Catalogue |
| My Work (Driver) | Driver self-service |
Header tools on every screen: global search (Ctrl K), notifications bell, Iris assistant, profile menu, tenant switcher (Safe-Fare Admin).

## Key concepts
See `terminology.md`. Most important: a **vehicle** is the registered bus/van; a **device** is the GPS/camera terminal fitted in it; **alarms** come from devices (AI events from AI cameras, routine alarms from the terminal); an **alert/incident** is the handling record for an alarm.

## Fleet time
Dates in the UI are shown in fleet time **IST (Asia/Kolkata)**.
