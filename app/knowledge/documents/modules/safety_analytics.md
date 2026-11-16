---
module: Safety Analytics
feature_keys:
- safety-analytics
- safety-trends
- events-by-type
- events-by-severity
- events-by-hour
- top-drivers
- top-vehicles
- risk
routes:
- /drive-vision/safety
roles:
- users with alarm.read
permissions:
- alarm.read
availability: VERIFIED LIVE (read)
technical_reference: api/modules/safety_analytics_api.md
---

# Safety Analytics

## 1. Purpose
Safety event trends for the fleet — totals, events per day, by type, by severity, by hour of day, the drivers and vehicles with most events — and the server-computed safety score tables (see `safety_scores.md`).

## 2. Navigation
Sidebar **Safety → Safety Analytics**. Subtitle "Event trends and safety scores for drivers and vehicles".

## 3. Sections
- **Date range**: Today · Last 7 days · Last 30 days (default).
- **Totals**: Events, Avg. resolution, severe share.
- **Events per day** ("All events and the severe share").
- **By event type**, **By severity** ("Severity labels as supplied by the server"), **By hour of day**.
- **Most events · drivers**, **Most events · vehicles**.
- **Safety scores** table (Scores for Drivers / Vehicles).

## 9. Workflows
**Which vehicles have the highest risk?** Safety Analytics → Date range → *Most events · vehicles*, or Safety scores → **Vehicles** → lowest score / most severe events. "Risk" is not a separate field; use score, severe count and penalty points from the server.
**Show safety analytics**: open the screen and choose the range.

## 16. Business rules
Only server numbers are shown; the old client-side scoring formula was removed.

## 18. Common questions
- **What is safety analytics?** Charts of safety events (AI events + routine alarms) over time and by type/severity, to find risky behaviour.
- **What is a severe event?** One the server classifies as severe; the severity scale itself is not documented.

## 19. Limitations
Heatmap and false-positive analytics are supported by the backend but not shown in the app.
