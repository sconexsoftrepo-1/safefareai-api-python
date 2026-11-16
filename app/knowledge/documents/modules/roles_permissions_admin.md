---
module: Roles and Permissions administration (Global Roles, Permission Catalogue)
feature_keys:
- roles
- global-roles
- permissions
- permission-catalogue
- role-permission-matrix
- assign-permissions
routes:
- /drive-vision/platform/roles
- /drive-vision/platform/permissions
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
availability: IMPLEMENTED, NOT VERIFIED here
technical_reference: api/modules/roles_permissions_admin_api.md
---

# Roles and Permissions administration

## 1. Purpose
Define global roles and which permission codes each role holds. Only the Safe-Fare Admin configures roles in the frontend; changes affect everyone with that role at their next sign-in or token refresh.

## 2. Navigation
**Platform → Global Roles** and **Platform → Permission Catalogue**.

## 3. Screens
- **Global Roles**: tabs Global roles / Tenant roles (view only); search ("Search code, description or id"), Role scope, Role flags; columns Code, Description, Scope, Flags (Protected, Full access, Not assignable), Active users; **New global role**, **Edit description**, **Delete role**, **Permissions** editor (Assigned / Not assigned / Changed → **Review changes**).
- **Permission Catalogue**: views Catalogue / Role permissions; filter by scope and code prefix; **New permission**, **Edit**, **Delete permission**; **Role permissions** matrix: Select role → tick permissions by module → **Save permissions** ("Replaces the role's whole permission list on the server").

## 6. Rules
Role code: uppercase letters, digits and `_`, starting with a letter (2–30). Permission code: lowercase dotted, e.g. `device.read` (max 60). Full-access roles have no editable list. Protected or in-use roles/codes are refused by the server.

## 9. Workflows
**Give a role a permission**: Global Roles → open role → Permissions → tick codes → Review changes → save. Or Permission Catalogue → Role permissions → Select role → tick → Save permissions.

## 18. Common questions
- **Why can't I access a menu?** Your role lacks the screen's permission code (see `roles_permissions.md`); the Safe-Fare Admin can add it here.
- **Can a tenant admin edit roles?** Not in this app (platform-only by product rule).

## 19. Limitations
Menu-level permissions per role aren't editable in the app. Changes have not been verified live.
