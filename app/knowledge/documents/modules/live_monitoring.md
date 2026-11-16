---
module: Live Monitoring
feature_keys:
- live-map
- realtime
- positions
- report-age
- live-video
- follow-vehicle
routes:
- /drive-vision/monitoring
- /drive-vision/monitoring?vehicle=<deviceId>
roles:
- any user with device.read
permissions:
- device.read
availability: VERIFIED LIVE
technical_reference: api/modules/live_monitoring_api.md
---

# Live Monitoring

## 1. Purpose
Map and list of every device's latest reported position, speed, battery and active alarm, refreshed automatically; open a device's live camera.

## 2. Navigation
Sidebar **Monitor → Live Monitoring**. Deep links: `?vehicle=<deviceId>` selects a device.

## 3. Screen
- Header line: "<n> online · <n> offline (server counts) · updated <time>"; **Refresh** ("Refresh positions now").
- **Vehicle list** with **Search vehicles** ("Name or device ID"), **Report age filter** (All · ≤ 5 min · ≤ 1 h · Stale · No position), **Group** (All groups), **Alarms** toggle ("Show only devices reporting an active alarm").
- **Live map** (MapLibre + MapTiler, or a coordinate-grid fallback when no map key is configured). "Nothing to plot" when no device has usable coordinates.
- **Device panel**: Speed, Heading, Odometer, Battery, Altitude, Position, Device time, Received, Video capable, raw sensor values; buttons **Track history** (opens Trips & Tracking) and **Details** (device detail page).
- **Live video** popup: opens when a device is picked from the list or map.

## 4. Report-age legend
| Label | Meaning |
|---|---|
| ≤ 5 min | Reported within 5 minutes (current) |
| ≤ 1 h | Reported within the last hour |
| Stale | Last report over 1 hour ago |
| No time | Device sent no report time |
Online/offline totals are the server's counts; undocumented device status codes are not used for colours or filters.

## 9. Workflows
**Find a vehicle on the map**: Live Monitoring → type its name or device ID in Search vehicles → pick it → map centres and the panel opens.
**Watch live camera**: pick the device → the Live video popup opens (vendor player, channels 1..camera count). If it says "Live video unavailable", the device has no terminal number or live video isn't configured for this installation.
**See where it has been**: device panel → **Track history**.

## 10–11. Roles / permissions
`device.read`. Drivers have no access.

## 16. Business rules
- Positions plotted only with valid WGS84 coordinates; (0,0) is treated as "no fix".
- `sensors` values are shown raw (units undocumented).

## 17. Errors
Realtime failure keeps the last data and shows the error; 503 = vendor unavailable.

## 18. Common questions
- **Why is a device showing offline?** The server reports it isn't sending data to the GPS vendor. Common causes (unverified for any specific device): vehicle ignition off / device powered down, no mobile network, SIM expired, device service expired, hardware fault. Check Last report time, Battery and the device's service expiry on its detail page.
- **Why is my vehicle not on the map?** It has no valid coordinates (no GPS fix or 0,0), or it's filtered out (group, report age, alarms-only, search).
- **How often does the map update?** Every 30 seconds by default, or press Refresh.

## 19. Limitations
- There is **no online/offline filter** on this screen. The Fleet Overview "Offline" tile opens this page, but the list is not filtered to offline devices. To find offline devices use the "Stale" report-age filter as an approximation, or ask Iris (live data).
- No instant (push) updates; the page refreshes on a timer.
