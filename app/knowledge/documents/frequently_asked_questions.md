---
title: Frequently asked questions
category: faq
---

# Frequently asked questions

**What is SafeFare?** An AI-powered fleet management and driver-safety app: live tracking, AI camera events, alarms, vehicles, devices, drivers, dispatch, workforce, reports and safety analytics, for multiple organisations. → `application_overview.md`

**What is the purpose of the dashboard?** Fleet Overview shows at a glance how many devices are online/offline, device health, safety events, today's trips/dispatches, pending leave/swaps, reminders and quick links. → `modules/dashboard_overview.md`

**What does each dashboard metric represent?** See the metric table in `modules/dashboard_overview.md` §4.

**What is a fleet owner?** The product role for a company that operates vehicles in SafeFare; it manages its own vehicles, drivers and operations. The backend role code for it is not confirmed yet. → `roles_permissions.md`

**What is a driver?** A person driving fleet vehicles, stored as a driver record; with a linked login, they use My Work. → `modules/drivers.md`

**What is a device?** The GPS/camera terminal installed in a vehicle (identified by its Device ID / terminal number). → `modules/devices_vehicles_assets.md`

**What is a vehicle?** The registered vehicle (vehicle number, type, make, model, status). → `modules/vehicle_registry.md`

**What is the difference between a vehicle and a device?** The vehicle is the bus/van itself; the device is the tracker fitted in it that sends positions, alarms and video. They're managed in two menus: **Vehicles** and **Vehicles & Assets**.

**What is an alarm?** An event reported by a device: AI events (ADAS/DSM/BSD camera detections) or routine alarms (terminal alarms). **What is an alert?** The handling record (incident) for an alarm. → `modules/alerts_incidents.md`

**What is an AI event?** An alarm from AI cameras about driver behaviour/state or road hazards, usually with image/video evidence. → `modules/ai_alarms.md`

**What is a geofence?** A virtual zone or route line; bound vehicles generate events when they enter/leave it or break its speed rule. → `modules/geofences.md`

**What does online/offline status mean?** Online = currently reporting to the GPS vendor; offline = not reporting. Counts come from the server. → `modules/live_monitoring.md`

**How can I add a vehicle?** Monitor → Vehicles → Register vehicle. → `workflows.md`

**How can I assign a driver?** Fleet → Drivers → open driver → Assign vehicle → Review → confirm. → `modules/driver_assignments.md`

**How can I check device status?** Vehicles & Assets → device → View; or Live Monitoring. → `modules/devices_vehicles_assets.md`

**How can I view historical videos?** Monitor → Historical Video → device → calendar day → recordings → export clip (in-app playback not yet available). → `modules/historical_video.md`

**How can I generate reports?** Monitor → Reports → type → time range → device. No download button yet. → `modules/reports.md`

**How do I change my password?** Settings → Change password (drivers: My Work → My Profile). → `modules/settings.md`

**How do I use the driver application?** Sign in as Tenant user with your driver login → My Work: start shift, checklist, accept/start/complete trips, end shift, leave, safety, profile. → `modules/driver_my_work.md`

**Why can't a driver access the admin dashboard?** Drivers only have `driver.app` + `own.data.read`; the dashboard needs `device.read`. → `roles_permissions.md`

**Can I see other organisations' data?** No; every record is tenant-scoped. Only the Safe-Fare Admin can view across tenants.

**Can I download reports or schedule them?** Not in the current app.

**Can I create a geofence?** Not in the current app (create/edit blocked).

**Can I send a command to a device?** Not in the current app (sending disabled).
