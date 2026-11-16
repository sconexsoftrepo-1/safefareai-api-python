---
title: Terminology
category: terminology
---

# SafeFare terminology

| Term | Meaning in SafeFare | Where |
|---|---|---|
| SafeFare AI | The fleet management & driver-safety web application | all |
| SafeFare server | The backend that stores data, checks permissions and talks to the GPS/video provider | — |
| Tenant / organisation | An isolated customer organisation; all data belongs to one tenant | Tenants |
| Tenant code | Code of the organisation entered at sign-in | Sign in |
| Safe-Fare Admin | Platform administrator (`platform=true`), signs in without a tenant code, manages tenants/roles | Platform |
| Tenant ADMIN | Full administrator inside one tenant | — |
| Fleet Owner | Product role for fleet operators; backend role code not confirmed (MANAGER "Fleet manager" exists) | — |
| Driver | Person driving fleet vehicles; driver logins use My Work | Drivers, My Work |
| Linked user | The login account linked to a driver record | Drivers |
| Sub-account | A user created under a parent user in the account hierarchy | Users |
| Role / permission | A role bundles permission codes like `device.read`; codes open screens and actions | Global Roles |
| All tenants mode | Safe-Fare Admin with no tenant selected: reads cover all tenants, writes disabled | tenant switcher |
| Vehicle | The registered physical vehicle (number, type, make, model, status) | Vehicles |
| Device / terminal | The GPS/MDVR/camera unit fitted in a vehicle, identified by Device ID (terminal no.) | Vehicles & Assets |
| Device group | Folder of devices (vendor account group) | Vehicles & Assets |
| Object type, protocol, device model | Vendor classification of a device (reference lists) | Register device |
| Online / offline | Whether a device is currently reporting (server counts from realtime) | Overview, Live Monitoring |
| Never online | Device that has never reported | Device health |
| Stale | Last report older than the threshold (1 h on Live Monitoring; > 24 h server count) | Overview |
| Report age | Time since a device's last report (≤ 5 min, ≤ 1 h, stale, no time) | Live Monitoring |
| Service expiry | Date the device's vendor service ends (`expiresAt`) | Device detail |
| Alarm | Event reported by a device | Alerts & Events |
| AI event | Alarm from AI cameras: ADAS, DSM, BSD | Alerts & Events › AI events |
| ADAS / DSM / BSD | Advanced Driver Assistance (road), Driver Status Monitoring (driver), Blind Spot Detection | AI events |
| Routine alarm | Non-AI terminal alarm (e.g. overspeed, SOS) | Alerts & Events › Routine alarms |
| Alert / incident | Handling record of an alarm (NEW, ACKNOWLEDGED, IN_PROGRESS, RESOLVED, DISMISSED) | Incidents |
| Outcome | Resolution reason: CONFIRMED_ALARM, FALSE_POSITIVE, TEST, DISPATCH_EMERGENCY, DISPATCH_TERMINAL, VOICE_COMMAND | Incidents |
| Severity | Server's severity value (scale undocumented) | Alerts |
| Evidence | Image/video attached to an alarm | Alerts |
| Safety score / grade | Server-computed score per driver/vehicle | Safety Analytics |
| Penalty points | Points the server adds for events, used in the score | Safety scores |
| Trip | Journey detected by the server from GPS (start → end) | Trips & Tracking |
| Track | Raw GPS points of a device for a time range | Track playback |
| Dispatch | Planned job given to a driver + vehicle (ASSIGNED, ACCEPTED, DECLINED, IN_PROGRESS, COMPLETED, CANCELLED) | Dispatch |
| Swap request | Request to move a dispatch to another driver (PENDING, APPROVED, REJECTED, CANCELLED) | Dispatch |
| Conflict check | Server validation of a dispatch draft (driver/vehicle busy, leave) | Dispatch |
| Assignment | Driver ↔ vehicle link for a period | Drivers |
| Shift | Driver's working period started/ended in My Work | Workforce, My Shifts |
| Availability | Driver status for a day: AVAILABLE, ASSIGNED, ON_SHIFT, ON_TRIP, ON_LEAVE | Workforce |
| Leave request | Driver leave (CASUAL, SICK, ANNUAL, UNPAID, OTHER; PENDING, APPROVED, REJECTED, CANCELLED) | Workforce, My Leave |
| Checklist | Pre-trip vehicle checklist (Pass/Fail items) | Workforce, Shift Checklist |
| Geofence | Virtual AREA (zone) or LINE (route) with rules | Geofences |
| Geofence event | Entry/exit/rule event of a bound device | Geofences |
| Recording calendar | Days with recorded video for a device | Historical Video |
| Clip export | Job that produces a downloadable video file | Historical Video |
| Channel | Camera number on a device | Historical Video, Live video |
| BMS | Bus boarding records used as ground truth for passenger counts | Sensors |
| IR sensor | Door sensor counting passengers in/out | Sensors |
| Over-capacity | More passengers than bus capacity (default 44) | Sensors |
| Alcohol check | Alcohol sensor result: DETECTED, NOT_DETECTED, INVALID_READING, NO_READING | Sensors |
| GPSTrackTech | GPS/video vendor behind devices, alarms and video | — |
| Live vs stored data | When the GPS provider doesn't answer, the server may show its last stored copy ("Stored data") or "No data from vendor" | vendor-backed screens |
| Reference (request id) | Code shown with an error message; quote it when reporting a problem | errors |
| IST | Fleet time zone Asia/Kolkata used in the UI | all |
| Iris | SafeFare's AI assistant | header |
