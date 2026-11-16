---
title: Architecture
category: architecture
sources:
- safefareai-ui-devlp-pavithra/package.json
- .env.example
- src/features/drive-vision/api/client.ts
- src/features/drive-vision/api/session.ts
- docs/current-architecture.md
- provided Swagger
- iris-ai project (previous audit)
---

# Architecture

```
Browser ─ SafeFare AI web UI (Next.js 16, React 19, TypeScript, Tailwind 4, shadcn/ui, MapLibre, Recharts)
   │  Bearer JWT (sessionStorage per tab, auto refresh)      NEXT_PUBLIC_API_BASE_URL=http://185.193.19.156:9096
   ▼
Safe-Fare Fleet BFF (Java/Spring Boot)  /api/v1/**   — tenant scoping, permissions, envelope {code,msg,data,total,extend}
   ├─ SafeFare SQL database ("Safe-Fare")              — schema NOT SUPPLIED
   └─ GPSTrackTech vendor APIs (devices, positions, alarms, video) — vendor-backed reads report extend.source/stale/fallbackReason
Live camera popup → vendor player https://y.gpstracktech.com (token NEXT_PUBLIC_GPS_VIDEO_API_TOKEN)
Map tiles → MapTiler (NEXT_PUBLIC_MAPTILER_KEY) or coordinate-grid fallback

Iris AI (FastAPI, Groq) — separate service; conversation DB "Safe-Fare-Python" (assistant_conversations, assistant_messages); not yet wired to the UI
```

## Frontend layout
- `src/app/drive-vision/**` — routes (thin pages).
- `src/components/drive-vision/<module>/` — screens and pure `*-model.ts` validation/logic (unit-tested in `tests/*.test.cjs`).
- `src/features/drive-vision/api/*-service.ts` — one service per backend area; `client.ts` (fetch, timeout 15 s, refresh, errors, `X-Request-Id`), `tenant-context.ts` (adds `X-Tenant-Id` for the Safe-Fare Admin's selected tenant).
- `src/features/drive-vision/access/access-policy.ts` — permission → screens/actions resolver.
- Legacy sample-data modules (`store/`, `mock-data/`, `services/`) are still imported by a few components (e.g. unused group/transfer dialogs) but no screen shows sample data.

## Environment variables (frontend `.env.example`)
`NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_API_TIMEOUT_MS` (15000), `NEXT_PUBLIC_API_DEBUG`, `NEXT_PUBLIC_DEFAULT_TENANT_CODE`, `NEXT_PUBLIC_MAPTILER_KEY`, `NEXT_PUBLIC_MAPTILER_MAP`, `NEXT_PUBLIC_MAP_STYLE_URL`, `NEXT_PUBLIC_GPS_VIDEO_API_TOKEN`; optional `NEXT_PUBLIC_REALTIME_POLL_MS` (default 30000, min 10000).

## Cross-cutting behaviour
- Errors: `ApiError` with kind (http, timeout, network, parse), status, `errorCode`, `fieldErrors`, `requestId` shown as a reference.
- 503 "unavailable" is never shown as zero/empty; missing numbers show "—".
- Undocumented codes are displayed raw, never interpreted.
- Polling only (no websockets/push).

## What is NOT in the provided material
Java source, SafeFare database schema, user guides. Backend behaviour is documented only from Swagger, backend contract files in `docs/contracts/` and the frontend team's live-verification evidence.
