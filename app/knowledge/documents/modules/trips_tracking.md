---
module: Trips & Tracking
feature_keys:
- trips
- trip-history
- route-playback
- track-playback
- trip-summary
- event-markers
routes:
- /drive-vision/trips
roles:
- users with track.read
permissions:
- track.read
availability: VERIFIED LIVE (read-only)
technical_reference: api/modules/trips_tracking_api.md
---

# Trips & Tracking

## 1. Purpose
Trip history detected by the server (start/end, distance, duration, driver, alarms) with route maps, plus raw GPS **track playback** for any device and time range.

## 2. Navigation
Sidebar **Monitor → Trips & Tracking**. Opened from Live Monitoring's **Track history** and vehicle detail **All trips**.

## 3. Views (**View** switch)
1. **Trips** (default): filters **Vehicle** (All vehicles / device) and **Date range** (Today · Last 7 days (default) · Last 30 days); **Trip summary**; table; selecting a trip shows its route, start/end pins, stops and events.
2. **Track playback**: device picker, **Time range** 24 h · 3 days · 7 days · Custom (**From (IST)**, **To (IST)**), **Position filter** (Located points · All points · Unlocated only), stats (Points (server count), Distance, Max reported speed, Recorded span), playback controls (**Back to first point**), event-marker pins.

## 7. Trip table columns
Started (or "In progress"), Vehicle, Driver, Distance, Duration, Alarms. Detail: Distance · duration, Driving · idle, Speed avg · max, Stops · alarms, Stops list.

## 9. Workflows
**How can I check today's trips?** Trips & Tracking → View **Trips** → Date range **Today** → (optional) choose a vehicle → read the table and the Trip summary; select a trip for its route.
**Replay where a vehicle went**: View **Track playback** → choose the device → time range → play.

## 10–11. Roles / permissions
`track.read`.

## 16. Business rules
Trips are detected by the backend (read-only here). Points without usable GPS are skipped and counted. A live trip has no end pin.

## 17. Errors
Empty track → "No points in this range"; unusable positions → "Nothing to draw"; route failure → "Couldn't load the route". An empty track may show as "unavailable" (known backend issue).

## 18. Common questions
- **What is a trip?** A journey the server detected from GPS data, from start to stop, with distance, duration and driver.
- **What's the difference between a trip and a dispatch?** A dispatch is planned work given to a driver (Dispatch screen); a trip is what the vehicle actually drove.
- **Can I create or edit trips?** Not in the app; trips are detected automatically.

## 19. Limitations
Trip write APIs unused. Track limited to 7 days per request.
