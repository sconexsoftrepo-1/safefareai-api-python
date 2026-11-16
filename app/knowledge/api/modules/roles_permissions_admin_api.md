---
module: Roles and Permissions administration (Global Roles, Permission Catalogue)
user_document: documents/modules/roles_permissions_admin.md
roles:
- Safe-Fare Admin only
permissions:
- role.read
- role.manage
- role.permission.read
- role.permission.create
- role.permission.delete
- role.permission.update
- permission.manage
apis:
- GET /api/v1/roles
- POST /api/v1/roles
- PUT /api/v1/roles/{id}
- DELETE /api/v1/roles/{id}
- GET /api/v1/roles/{id}/permissions
- POST /api/v1/roles/{id}/permissions
- PUT /api/v1/roles/{id}/permissions
- DELETE /api/v1/roles/{id}/permissions
- GET /api/v1/permissions
- POST /api/v1/permissions
- PUT /api/v1/permissions/{code}
- DELETE /api/v1/permissions/{code}
sources:
- src/app/drive-vision/platform/roles/page.tsx
- src/app/drive-vision/platform/permissions/page.tsx
- src/components/drive-vision/platform/global-roles.tsx
- src/components/drive-vision/platform/role-permission-editor.tsx
- src/components/drive-vision/platform/permission-catalog.tsx
- src/components/drive-vision/platform/role-permission-matrix.tsx
- src/components/drive-vision/platform/role-permission-model.ts
- src/features/drive-vision/api/role-admin-service.ts
server_route_paths:
- /platform/roles
- /platform/permissions
status: IMPLEMENTED (docs/phase7-role-permission-report.md); writes NOT VERIFIED live in this audit
---

# Roles and Permissions administration (Global Roles, Permission Catalogue) — API and implementation reference

Technical companion of `documents/modules/roles_permissions_admin.md`. For the Iris tool layer and developers; not for quoting to end users.


## Technical details referenced by the user document

- **Platform → Global Roles** (`/drive-vision/platform/roles`) and **Platform → Permission Catalogue** (`/drive-vision/platform/permissions`).
- `GET/PUT /roles/{id}/menu-permissions` unused. Writes not verified live.
