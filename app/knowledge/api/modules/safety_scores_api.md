---
module: Safety Scores
user_document: documents/modules/safety_scores.md
roles:
- fleet users with alarm.read; drivers for their own score
permissions:
- alarm.read
- own.data.read (driver)
apis:
- GET /api/v1/safety/scores/drivers
- GET /api/v1/safety/scores/vehicles
- GET /api/v1/drivers/{id}/safety-score
- GET /api/v1/drivers/{id}/safety-events
- GET /api/v1/driver/safety-score
- GET /api/v1/driver/safety-events
sources:
- src/components/drive-vision/safety/safety-analytics.tsx
- src/components/drive-vision/drivers/drivers-page.tsx
- src/components/drive-vision/operations/my-work-page.tsx
status: VERIFIED LIVE (read) 2026-10-29
---

# Safety Scores — API and implementation reference

Technical companion of `documents/modules/safety_scores.md`. For the Iris tool layer and developers; not for quoting to end users.

## 15. Response
`ScoreDto {id, name, alarmCount, severeCount, penaltyPoints, distanceKm, tripCount, score, grade}`.
