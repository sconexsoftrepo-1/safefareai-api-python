---
module: Platform Overview (Safe-Fare Admin dashboard)
feature_keys:
- platform-dashboard
- all-tenants
- platform-kpis
routes:
- /drive-vision/platform
roles:
- Safe-Fare Admin only
permissions:
- tenant.all + platform=true; widgets device.read
- alarm.read
- group.read
availability: IMPLEMENTED, NOT VERIFIED here
technical_reference: api/modules/platform_overview_api.md
---

# Platform Overview

## 1. Purpose
Home screen for the **Safe-Fare Admin** (platform administrator): tenants, devices, alerts and activity across the whole platform.

## 2. Navigation
Sidebar **Platform → Platform Overview**. It is the Safe-Fare Admin's landing page after sign-in.

## 3–4. Sections
- **Tenants** count and per-tenant table (Tenant, Status, Users, Drivers — "Per-tenant counts reported by the server (always platform-wide)").
- **Device groups** count.
- **Fleet operations** (status breakdown).
- **Alerts & AI events**: Open alerts, *By severity (server scale)*, *Recent open events*.
- **Platform quick links**: Fleet Overview ("All-tenant fleet view"), Alerts & Events, Accounts & roles.
- **Refresh** ("Refresh platform data").

## 5–8.
No forms. Each widget shows "No permission for this widget" or "Nothing returned" when applicable.

## 9. Workflow — work inside one tenant
1. From Platform Overview open **Tenants** (or the tenant switcher in the top bar).
2. Select a tenant → all data and actions apply to that tenant.
3. Use **Return to all tenants** to go back to platform-wide view.

## 10–11. Roles / permissions
Only `platform === true` **and** `tenant.all`. A tenant ADMIN never sees it even with the same codes.

## 16. Business rules
Figures are platform-wide unless a tenant is selected. Severity is shown on the server's raw scale.

## 18. Common questions
- **How many organisations are registered?** Platform Overview → Tenants count (Safe-Fare Admin only).
- **Why can't a tenant admin see Platform Overview?** It requires the platform flag; tenant administrators are not platform users.

## 19. Limitations
NOT VERIFIED live; per-tenant user/driver counts depend on what the server returns.
