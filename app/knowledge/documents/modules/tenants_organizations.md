---
module: Organizations / Tenants
feature_keys:
- tenants
- organizations
- tenant-switcher
- tenant-selection
- create-tenant
- all-tenants-mode
routes:
- /drive-vision/tenants
roles:
- Safe-Fare Admin only
permissions:
- tenant.all (+ platform=true)
availability: IMPLEMENTED; create NOT VERIFIED
technical_reference: api/modules/tenants_organizations_api.md
---

# Organizations / Tenants

## 1. Purpose
A **tenant** is an organisation (fleet operator) on SafeFare. All business data (devices, vehicles, drivers, alerts…) belongs to exactly one tenant. Tenant users only ever see their own tenant. The Safe-Fare Admin manages tenants and chooses which tenant to work in.

## 2. Navigation
- Sidebar **Platform → Tenants**.
- **Tenant switcher** in the top bar (Safe-Fare Admin only): "Tenant context", search "Search name, code or id", **All tenants** ("Platform-wide reads · no tenant actions"), **Manage tenants**.

## 3. Screens
- Tenant list with search ("Search by name, code or id"), **Filter by status** (All / statuses returned), paging (Previous/Next page).
- **Details** side panel (shows the tenant's details; viewing doesn't change your tenant selection).
- **Create tenant** panel with **Review** step.
- Banner "Working in <tenant>" / "Viewing all tenants" + **Return to all tenants**.

## 4–5. Features and buttons
| Button | Action |
|---|---|
| Select (row) | Work inside that tenant. |
| Return to all tenants | Clears the selection (platform-wide reads). |
| Refresh | Reloads the tenant list. |
| Create tenant → Review → confirm | Creates the tenant. |
| Details | Shows the row's data only. |

## 6. Create tenant form
| Field | Required | Rule |
|---|---|---|
| Tenant name | yes | "Enter a tenant name." |
| Tenant code | no | No spaces; empty → server generates the code. |
| Time zone | yes | Valid IANA zone from the list, e.g. Asia/Kolkata. |
| Status | yes | From the allowed list (`CreateTenantRequest.status`: ACTIVE, SUSPENDED). |
| S3 prefix | no | Optional storage prefix; sent empty if blank. |
Review text: "Creating a tenant can't be undone from this app. No users or tenant administrator are created."

## 9. Workflows
**Select a tenant (Safe-Fare Admin)**: top bar tenant switcher → search → pick tenant → banner "Working in …". Tenant-scoped create/edit buttons become available.
**Create a tenant**: Tenants → **Create tenant** → fill name, (code), time zone, status, (S3 prefix) → **Review** → confirm. Then create its users in Users & Sub-Accounts after selecting the tenant.

## 10–11. Roles / permissions
Safe-Fare Admin (`platform=true`) with `tenant.all`. Tenant users never see tenants.

## 16. Business rules
- The Safe-Fare Admin has no tenant of its own. Reads without a tenant cover **every** tenant; creating or changing records requires a selected tenant. The app hides tenant writes in "All tenants" mode and shows "Select a tenant to create or change records on this page" + **Select tenant**.
- Tenant users' tenant comes from their token and can't be changed; another tenant's id → 403 `TENANT_ACCESS_DENIED`; another tenant's record → 404.

## 17. Errors
"Couldn't load tenants" + Retry; create errors shown per field; 400 `TENANT_REQUIRED` explained as "Select a tenant first".

## 18. Common questions
- **What is a tenant / organisation?** Your company's isolated space in SafeFare.
- **Why are the create buttons missing?** You're the Safe-Fare Admin in "All tenants" mode — select a tenant first.
- **Can a fleet owner see another organisation's data?** No. Every record is scoped to the caller's tenant; other tenants' records answer 404.
- **Can I edit or delete a tenant?** Not in the app; there is no screen for it yet.

## 19. Limitations
Editing, suspending or deleting a tenant is not available in the app.
