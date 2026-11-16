---
module: Safety Analytics
user_document: documents/modules/safety_analytics.md
roles:
- users with alarm.read
permissions:
- alarm.read
apis:
- GET /api/v1/safety/analytics
- GET /api/v1/safety/scores/drivers
- GET /api/v1/safety/scores/vehicles
sources:
- src/app/drive-vision/safety/page.tsx
- src/components/drive-vision/safety/safety-analytics.tsx
- src/features/drive-vision/api/insight-service.ts
status: VERIFIED LIVE (read) 2026-10-29
---

# Safety Analytics — API and implementation reference

Technical companion of `documents/modules/safety_analytics.md`. For the Iris tool layer and developers; not for quoting to end users.

## 13–15. API
`GET /safety/analytics?from&to` → `SafetyAnalyticsDto` (totals, by day/type/severity/hour, top drivers/vehicles). Unused in Swagger: `GET /safety/heatmap`, `GET /safety/false-positives`.

## Technical details referenced by the user document

- Sidebar **Safety → Safety Analytics** (`/drive-vision/safety`). Subtitle "Event trends and safety scores for drivers and vehicles".
