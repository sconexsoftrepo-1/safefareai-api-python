---
module: Users & Sub-Accounts
feature_keys:
- users
- sub-accounts
- create-user
- edit-user
- disable-user
- unlock-user
- reset-password
- user-hierarchy
- roles-view
routes:
- /drive-vision/users
roles:
- users with user.read
permissions:
- user.read
- user.create
- user.update
- user.delete (unused)
- role.read / role.permission.read (roles tab)
availability: Read VERIFIED; writes NOT VERIFIED; delete missing
technical_reference: api/modules/users_sub_accounts_api.md
---

# Users & Sub-Accounts

## 1. Purpose
Manage login accounts of the organisation: users, their role, status, and the parent/sub-account hierarchy.

## 2. Navigation
Sidebar **Administration → Users & Sub-Accounts**. Subtitle "Account tree, roles and permissions".

## 3. Views (**View**)
- **Users**: columns User, Role, Status, Last sign-in ("Never"), Created, plus "Locked" badge. Filters: **Search users** ("Name, email or phone"), Status (Any status · Active · Invited · Disabled), Role (Any role). Paged 20.
- **Hierarchy**: "Account hierarchy — Parent and sub-accounts as returned by the server".
- **Roles & permissions** (read-only): roles with Protected / Not assignable badges and their permission codes; **Permission catalogue**.
- User drawer: Status, Role, Phone, Parent account, Locale · time zone, Failed sign-ins, Locked until, Last sign-in, Created, Updated; buttons **Edit**, **Disable/Enable**, **Unlock**, **Reset password**.

## 6. Forms
New user / Edit: Display name (**required**, ≤150), Email (valid, ≤320), Phone (5–30: digits, spaces, + ( ) -), Initial password (**required on create**, ≤72), Locale (e.g. en or en_IN), Time zone (≤50), **Role** (required, assignable roles). Reset password: New password (≤72), Confirm password (must match).

## 9. Workflows
**Create a user**: Users & Sub-Accounts → **New user** → name, email/phone, initial password, role → save. (Safe-Fare Admin: select the tenant first.)
**Create a driver login**: create the user with the **DRIVER** role, then link it in Drivers → Edit → Linked user id.
**Unlock an account** after too many failed sign-ins: open user → **Unlock**.
**Reset someone's password**: open user → **Reset password** → new + confirm.
**Disable a user**: open user → Disable (status ACTIVE ⇄ DISABLED).

## 16. Business rules
Your own account's status/password can't be changed here (use Settings). Edit resends the current parent account so the hierarchy doesn't change. Roles are read-only here; only the Safe-Fare Admin edits roles (Global Roles).

## 18. Common questions
- **What is a sub-account?** A user created under another user (parent) in the account hierarchy.
- **Why is a user locked?** Too many failed sign-ins; see "Failed sign-ins" / "Locked until"; use **Unlock**.
- **What user statuses exist?** User status filter values: Active, Invited, Disabled (status changes in the app: ACTIVE ⇄ DISABLED).
- **Can I delete a user?** No. Delete user is not exposed in the app; disable the user instead.

## 19. Limitations
Delete user not exposed. Roles not editable here.
