---
module: Organizations / Tenants
user_document: documents/modules/tenants_organizations.md
roles:
- Safe-Fare Admin only
permissions:
- tenant.all (+ platform=true)
apis:
- GET /api/v1/platform/tenants
- POST /api/v1/platform/switch-tenant
- POST /api/v1/platform/tenants
sources:
- src/app/drive-vision/tenants/page.tsx
- src/components/drive-vision/platform/tenant-management.tsx
- src/components/drive-vision/platform/tenant-management-model.ts
- src/components/drive-vision/platform/tenant-create-panel.tsx
- src/components/drive-vision/platform/tenant-create-model.ts
- src/components/drive-vision/app-shell/tenant-switcher.tsx
- src/components/drive-vision/shared/tenant-required.tsx
- src/features/drive-vision/api/platform-service.ts
- src/features/drive-vision/api/tenant-context.ts
- src/features/drive-vision/api/tenant-scope.ts
- src/features/drive-vision/store/tenant-store.ts
server_route_paths:
- /tenants
status: IMPLEMENTED (docs/phase5-tenant-context-report.md, docs/phase6-tenant-management-report.md); create tenant NOT VERIFIED live in this audit
---

# Organizations / Tenants — API and implementation reference

Technical companion of `documents/modules/tenants_organizations.md`. For the Iris tool layer and developers; not for quoting to end users.

## 13–15. APIs
- `GET /platform/tenants?status` → `[TenantDto]` (status ACTIVE/SUSPENDED/CLOSED).
- `POST /platform/switch-tenant` (tenant.all).
- `POST /platform/tenants` body `CreateTenantRequest` (contract from backend 2026-11-02; now in the provided Swagger).
- In Swagger but **not used by the frontend**: `GET/PUT/DELETE /platform/tenants/{id}`.

## Technical details referenced by the user document

- Sidebar **Platform → Tenants** (`/drive-vision/tenants`).
| Select (row) | `POST /platform/switch-tenant` → work inside that tenant. |
| Refresh | Reloads `GET /platform/tenants`. |
| Create tenant → Review → confirm | `POST /platform/tenants`. |
- The Safe-Fare Admin has no tenant of its own. Reads without a tenant cover **every** tenant; create/update/delete without `tenantId`/`X-Tenant-Id` answer 400 `TENANT_REQUIRED`. The app hides tenant writes in "All tenants" mode and shows "Select a tenant to create or change records on this page" + **Select tenant**.
- **Can I edit or delete a tenant?** Not in the app. `PUT/DELETE /platform/tenants/{id}` exist in Swagger but have no screen.
- Edit/suspend/delete tenant APIs exist in Swagger but have no screen. Tenant detail endpoint (`GET /platform/tenants/{id}`) unused.
