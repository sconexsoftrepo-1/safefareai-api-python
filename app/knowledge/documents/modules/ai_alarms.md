---
module: AI Alarms (AI events)
feature_keys:
- ai-events
- ai-alarms
- adas
- dsm
- bsd
- driver-fatigue
- distraction
- ai-event-evidence
routes:
- /drive-vision/alerts?kind=ai
roles:
- users with alarm.read
permissions:
- alarm.read
availability: VERIFIED LIVE
technical_reference: api/modules/ai_alarms_api.md
---

# AI Alarms (AI events)

## 1. Purpose
Events detected by the device's AI cameras — ADAS (forward collision, lane departure…), DSM (driver fatigue, distraction, phone, smoking…), BSD (blind spot) — with image/video evidence. The exact list of AI alarm types is supplied by the SafeFare server and can differ per installation.

## 2. Navigation
Safety → Alerts & Events → **Alarm kind = AI events**.

## 3. Screen
Filters: Time range (Today · Last 7 days · Last 30 days), **All devices**, **All alarm types**, Clear filters. Columns: Event (with "Video attached"/"Image attached" markers), Device, Time, Duration, Speed, Severity (raw), Status. Drawer: Evidence from the vendor (Image, Video), Terminal, Started, Ended, Coordinates, Handling status, Vendor time, Reference, **Track history for this device**.

## 9. Workflow — How can I view AI alarms?
Safety → **Alerts & Events** → choose **AI events** → set the Time range (e.g. Today) → optionally filter device/type → select a row to see image/video evidence.

## 18. Common questions
- **What is an AI event?** An alarm raised by the camera's AI (ADAS/DSM/BSD) about driving behaviour or driver state, usually with a photo or clip.
- **Show the latest AI events**: AI events tab, Time range Today, newest first — or ask Iris (live data).

## 19. Limitations
Severity scale undocumented (raw value). Some evidence links may not open if the vendor returns a placeholder address. Handling is done on the Incidents tab.
