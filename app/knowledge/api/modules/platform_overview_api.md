---
module: Platform Overview (Safe-Fare Admin dashboard)
user_document: documents/modules/platform_overview.md
roles:
- Safe-Fare Admin only
permissions:
- tenant.all + platform=true; widgets device.read
- alarm.read
- group.read
apis:
- GET /api/v1/platform/tenants
- GET /api/v1/dashboard/overview
- GET /api/v1/dashboard/fleet-status
- GET /api/v1/dashboard/safety-events
- GET /api/v1/groups
sources:
- src/app/drive-vision/platform/page.tsx
- src/components/drive-vision/dashboard/platform-dashboard.tsx
- src/components/drive-vision/dashboard/platform-dashboard-model.ts
status: IMPLEMENTED (docs/phase4-platform-dashboard-report.md); live data NOT VERIFIED in this audit
---

# Platform Overview (Safe-Fare Admin dashboard) — API and implementation reference

Technical companion of `documents/modules/platform_overview.md`. For the Iris tool layer and developers; not for quoting to end users.

## 13–15. API
`GET /platform/tenants?status` → `[TenantDto]` (not paged); dashboard endpoints as in `dashboard_overview.md` (no tenant header = all tenants).

## Technical details referenced by the user document

- Sidebar **Platform → Platform Overview** (`/drive-vision/platform`). It is the Safe-Fare Admin's landing page after sign-in.
- 2. Select a tenant → the app calls `POST /platform/switch-tenant` and all data/actions apply to that tenant.
- **How many organisations are registered?** Platform Overview → Tenants count (Safe-Fare Admin only; from `GET /platform/tenants`).
- NOT VERIFIED live in this audit; per-tenant user/driver counts depend on what `TenantDto` returns.
