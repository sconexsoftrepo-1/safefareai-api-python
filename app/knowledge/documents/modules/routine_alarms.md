---
module: Routine Alarms
feature_keys:
- routine-alarms
- alarms
- overspeed
- sos
- power-cut
- geofence-alarm
- device-alarm
routes:
- /drive-vision/alerts?kind=routine
roles:
- users with alarm.read
permissions:
- alarm.read
availability: VERIFIED LIVE
technical_reference: api/modules/routine_alarms_api.md
---

# Routine Alarms

## 1. Purpose
Non-AI alarms reported by the GPS terminal (for example overspeed, SOS/emergency, power/disconnection, geofence entry/exit — the exact types are supplied by the server; NOT VERIFIED per tenant).

## 2. Navigation
Safety → Alerts & Events → **Alarm kind = Routine alarms**.

## 3. Screen
Same filters, columns and drawer as AI events (see `ai_alarms.md`).

## 9. Workflow — Show today's alarms
Alerts & Events → **Routine alarms** (and **AI events**) → Time range **Today**. The tab chips show the total for each kind. Fleet Overview's Fleet activity chart shows both kinds together.

## 17. Errors
503 → "Routine alarms unavailable" (never shown as zero).

## 18. Common questions
- **How many alarms this month?** Alerts & Events, Time range Last 30 days (closest option; there is no calendar-month option) — the tab count is the server total. Or ask Iris (live data).

## 19. Limitations
Alarm rules that control how alarm types are handled have no screen.
