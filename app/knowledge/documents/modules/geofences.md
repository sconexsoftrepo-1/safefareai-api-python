---
module: Geofences
feature_keys:
- geofences
- zones
- route-lines
- geofence-events
- entry-exit
- speed-limit
- voice-prompts
routes:
- /drive-vision/geofences
roles:
- users with geofence.read
permissions:
- geofence.read
- geofence.delete
- geofence.create (unused)
- geofence.update (unused)
availability: Read VERIFIED; create/edit NOT IMPLEMENTED
technical_reference: api/modules/geofences_api.md
---

# Geofences

## 1. Purpose
A **geofence** is a virtual boundary on the map — an **area (zone)** or a **line (route corridor)** — bound to groups or devices, with rules (entry/exit, speed limit) that generate geofence events/alarms and optional voice broadcasts.

## 2. Navigation
Sidebar **Manage → Geofences**. Subtitle "Zones, route lines and their alert rules".

## 3. Screen
- **Shape** filter: All · Zones (AREA) · Lines (LINE); list + map (AREA rings, LINE polylines; invalid geometry listed with the reason).
- Detail: Bound to (groups/devices), Rule codes, Max speed / Speed limit, Area type code, Voice broadcasts, Points, Synced; **Delete**.
- **Geofence events** (scoped to the selected geofence): Date range (Today · Last 7 days · Last 30 days), event-type chips from the summary ("All types"); columns Time, Event, Geofence, Device, Speed, Duration.
- **Geofence voice prompts** ("Read-only list from the server").

## 5. Buttons
**Delete** → "Delete geofence" ("The geofence and its rules are removed on the server and from the devices it's bound to. This can't be undone here.") — needs `geofence.delete` (+tenant).

## 9. Workflows
**Show the latest geofence events**: Geofences → select a geofence (or none for all) → Geofence events → Today/7 days.
**Create a geofence**: NOT AVAILABLE in the app — create/edit are blocked until the backend documents the rule, area and colour codes.

## 16. Business rules
Rule codes, area type and colour index meanings are undocumented → shown raw. The screen shows whether data is "Stored data" or "Live vendor data".

## 18. Common questions
- **What is a geofence?** A virtual zone or route line; when a bound vehicle enters/leaves it or breaks its speed rule, a geofence event is recorded.
- **Can I draw a circle?** No; SafeFare supports only AREA (polygon) and LINE shapes, and creation isn't enabled yet.

## 19. Limitations
Create/edit missing. The stored/live label for route lines may be inaccurate (known backend issue).
