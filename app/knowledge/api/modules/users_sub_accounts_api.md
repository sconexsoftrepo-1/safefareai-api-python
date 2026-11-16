---
module: Users & Sub-Accounts
user_document: documents/modules/users_sub_accounts.md
roles:
- users with user.read
permissions:
- user.read
- user.create
- user.update
- user.delete (unused)
- role.read / role.permission.read (roles tab)
apis:
- GET /api/v1/users
- GET /api/v1/users/{id}
- GET /api/v1/users/tree
- POST /api/v1/users
- PUT /api/v1/users/{id}
- PATCH /api/v1/users/{id}/status
- POST /api/v1/users/{id}/unlock
- POST /api/v1/users/{id}/password
- GET /api/v1/roles
- GET /api/v1/permissions
sources:
- src/app/drive-vision/users/page.tsx
- src/components/drive-vision/users/users-page.tsx
- src/components/drive-vision/users/users-model.ts
- src/features/drive-vision/api/admin-service.ts
status: Read and tree VERIFIED LIVE 2026-10-27; create/edit/status/unlock/reset IMPLEMENTED, NOT VERIFIED; delete NOT IMPLEMENTED
---

# Users & Sub-Accounts — API and implementation reference

Technical companion of `documents/modules/users_sub_accounts.md`. For the Iris tool layer and developers; not for quoting to end users.


## Technical details referenced by the user document

- Sidebar **Administration → Users & Sub-Accounts** (`/drive-vision/users`). Subtitle "Account tree, roles and permissions".
- **Can I delete a user?** No. Delete user is not exposed in the app (API `DELETE /users/{id}` exists but its cascade effect is undocumented); disable the user instead.
- Delete user not exposed (cascade undocumented, #24). Roles not editable here.
