---
module: Safety Scores
feature_keys:
- safety-score
- driver-score
- vehicle-score
- grade
- penalty-points
- my-safety-score
routes:
- /drive-vision/safety (Safety scores)
- /drive-vision/drivers (driver drawer)
- /drive-vision/my-work/safety
roles:
- fleet users with alarm.read; drivers for their own score
permissions:
- alarm.read
- own.data.read (driver)
availability: VERIFIED LIVE (read)
technical_reference: api/modules/safety_scores_api.md
---

# Safety Scores

## 1. Purpose
A server-computed **score** and **grade** per driver or vehicle for a period, based on alarm counts, severe events and penalty points relative to trips and distance.

## 3. Where
- Safety Analytics → **Safety scores** ("Server-computed score and grade per driver or vehicle"), **Scores for** Drivers / Vehicles. Columns: Driver/Vehicle, Score (with grade), Alarms, Severe, Penalty pts, Trips, Distance. Server-paged.
- Drivers → driver drawer → Safety (Score, Alarms · severe, Distance; last 30 days).
- Driver app → My Work → **My Safety** (Safety score, last 30 days; Events by type; Recent safety events).

## 9. Workflows
**Check a driver's safety score**: Drivers → open the driver → Safety panel; or Safety Analytics → Safety scores → Drivers.
**Show the safety scores of my vehicles**: Safety Analytics → Safety scores → **Vehicles**.
**Driver: show my safety score**: My Work → **My Safety**.

## 15. What the score fields mean
- **Score** and **grade**: the overall result for the period (higher is safer — NOT VERIFIED; scale not documented).
- **Alarms** / **Severe**: number of safety events and how many were severe.
- **Penalty points**: points the server adds for safety events; they lower the score.
- **Trips** and **Distance**: how much was driven in the period, for context.

## 16. Business rules
The scoring formula is defined by the backend and is NOT DOCUMENTED; Iris must not explain it beyond these fields.

## 18. Common questions
- **How is the safety score calculated?** By the SafeFare server from alarms, severe events and penalty points over the period; the exact formula is not documented.
- **Why does a driver have no score?** No data for the period ("The server returned no score for this period").
