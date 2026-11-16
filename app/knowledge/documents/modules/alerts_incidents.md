---
module: Alerts & Events — Incidents (alert handling)
feature_keys:
- alerts
- incidents
- acknowledge
- resolve
- dismiss
- reopen
- comment
- evidence
- alert-handling
- open-alerts
routes:
- /drive-vision/alerts
- /drive-vision/alerts?kind=incidents
roles:
- users with alarm.read; handling needs alarm.handle
permissions:
- alarm.read
- alarm.handle
availability: Read VERIFIED; actions NOT VERIFIED; assign NOT AVAILABLE
technical_reference: api/modules/alerts_incidents_api.md
---

# Alerts & Events — Incidents

## 1. Purpose
An **alert (incident)** is an alarm that needs human handling. Operators acknowledge it, add comments, then resolve (with an outcome) or dismiss it; closed alerts can be reopened. The Alerts & Events screen has three tabs: **Incidents**, **AI events** (`ai_alarms.md`) and **Routine alarms** (`routine_alarms.md`).

## 2. Navigation
Sidebar **Safety → Alerts & Events**. Tab chosen with **Alarm kind**.

## 3. Incidents tab
- Filters: **Time range** (Today · Last 7 days (default) · Last 30 days), **Alarm type**, device, **Search alerts** (Keyword), **Open only**, **Clear filters**; **Refresh**/"Load again up to the current time".
- Columns: Alert, Device, Time, Severity (raw value; "the scale is undocumented"), Status, Assignee.
- Drawer: Kind, Driver (server), Location, Handled, **Evidence** (Open links), **History** of actions, action buttons.

## 5. Actions (need `alarm.handle`; each asks for confirmation)
| Button | What it does |
|---|---|
| Acknowledge | "Records that you have seen the alert." |
| Comment / Add comment | "Adds a note to the alert's history." (note required) |
| Resolve | "Closes the alert with an outcome." — **Outcome** required |
| Dismiss | "Closes the alert without a resolution outcome." |
| Reopen | "Returns a closed alert to open handling." |
Notes ≤ 1000 characters. Resolve outcomes: CONFIRMED_ALARM, FALSE_POSITIVE, TEST, DISPATCH_EMERGENCY, DISPATCH_TERMINAL, VOICE_COMMAND.

## 9. Workflows
**Handle an alert**: Alerts & Events → **Incidents** → (Open only) → open the alert → review Evidence and Location → **Acknowledge** → add comments as you investigate → **Resolve** with an outcome (or **Dismiss**).
**How do I view alarms?** Alerts & Events → choose **Incidents**, **AI events** or **Routine alarms** → set Time range and filters.

## 16. Business rules
Transitions are decided by the server; all actions are offered and the server may reject one (409). The driver shown is the one reported by the server, never derived from current assignment.

## 17. Errors
"The server rejected the action"; evidence links only for http(s) (placeholder hosts → "Link not usable").

## 18. Common questions
- **What is an alarm vs an alert?** An *alarm* is an event reported by the device (AI event or routine alarm). An *alert/incident* is the handling record the operator works on.
- **Can I assign an alert to someone?** Not yet. Assigning alerts to a person isn't available in the app until a backend issue is fixed.
- **Why is an alarm missing?** Check the time range and filters, whether it's an AI event or routine alarm (different tabs), and the vendor feed (503 = unavailable).
- **What alert statuses exist?** Alert handling status values: NEW, ACKNOWLEDGED, IN_PROGRESS, RESOLVED, DISMISSED.

## 19. Limitations
Assigning an alert and the high-priority handling steps are not available in the app. In rare cases the status shown and the action history may disagree (known backend issue).
