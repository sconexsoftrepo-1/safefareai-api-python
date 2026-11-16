---
module: Authentication and Sign-in
feature_keys:
- login
- logout
- session
- token-refresh
- access-denied
routes:
- /login
- /login?next=…
roles:
- Safe-Fare Admin
- Tenant ADMIN
- Fleet Owner
- Driver
- any tenant user
permissions:
- none (public) for login/refresh
- any signed-in user for logout/me
availability: VERIFIED LIVE
technical_reference: api/modules/authentication_login_api.md
---

# Authentication and Sign-in

## 1. Purpose
Signs a user in to SafeFare AI, keeps the session alive with token refresh, loads the user's identity and permissions, and decides which screens they can open.

## 2. Navigation and route
- Sign-in page: opened automatically when you're not signed in; after signing in you return to the page you wanted.
- Sign-out: avatar/profile menu in the top bar → **Sign out**. The access-denied panel also offers **Sign out**.

## 3. Screens
- **Sign in** form with an **Account type** switch: **Tenant user** or **Safe-Fare Admin**.
- "Your session expired. Please sign in again." banner when a session ended.
- Access-denied panel (route guard): "You don't have access to this page", "No access for this account yet", or "Page not found".
- "Couldn't load your session" panel with **Try again** when your session can't be loaded.

## 4. Features
- Two sign-in modes on one form (tenant vs platform admin).
- Your session is kept in the current browser tab (it survives a reload but ends when the tab is closed).
- The session is renewed automatically before it expires.
- Your permissions decide which menus and pages you can open.
- Landing page after sign-in: Platform Overview for the Safe-Fare Admin, otherwise Fleet Overview, otherwise the first screen the user may open; drivers land in My Work.

## 5. Buttons and actions
| Button | Action |
|---|---|
| Tenant user / Safe-Fare Admin | Switches which fields are required. |
| Sign in | Signs you in. |
| Sign out | Ends your session. |
| Try again | Reloads your session. |

## 6. Form fields and validation
| Field | Required | Max length | Notes |
|---|---|---|---|
| Tenant code | Tenant user: yes. Safe-Fare Admin: not shown, never sent | 50 | May be pre-filled. |
| Email or username | yes | 320 | Trimmed. |
| Password | yes | 72 | Never trimmed or logged. |
Error text pattern: "<Label> is required." / "<Label> must be at most N characters."

## 7–8. Tables, search, paging
Not applicable.

## 9. Workflows
**Sign in as a tenant user (Fleet Owner, tenant admin, driver, staff)**
1. Open the app; you are sent to **Sign in**.
2. Keep **Account type = Tenant user**.
3. Enter **Tenant code** (your organisation's code), **Email or username** and **Password**.
4. Select **Sign in**. You land on Fleet Overview (fleet users) or My Work (drivers).

**Sign in as the Safe-Fare Admin**
1. Choose **Account type = Safe-Fare Admin** ("Safe-Fare platform administrators sign in without a tenant code").
2. Enter login and password → **Sign in**. You land on **Platform Overview** in "All tenants" mode. Select a tenant from the tenant switcher before creating or changing tenant records.

**Sign out**: profile menu (top right) → **Sign out**.

## 10. Roles
Everyone signs in here. What they see afterwards depends on permissions (see `roles_permissions.md`).

## 11. Permission codes
Anyone can open the sign-in page; everything else needs a signed-in user.

## 16. Business rules
- The tenant code is used only for tenant users.
- `platform === true` identifies the Safe-Fare Admin; a role code never grants access by itself.
- An identity with no permissions opens no screen ("No access for this account yet").
- `?next=` only accepts safe in-app paths.

## 17. Error handling
- 401 `INVALID_CREDENTIALS` → wrong tenant code, login or password (observed live). 400 `VALIDATION_FAILED` → field errors shown per field.
- Expired session → redirect to sign-in with "Your session expired" message.
- Session can't be loaded → "Couldn't load your session" + **Try again**.

## 18. Common questions
- **Why does login fail?** Check the account type: tenant users need the correct tenant code; the Safe-Fare Admin must choose "Safe-Fare Admin" and leave the tenant code out. Wrong credentials answer 401 `INVALID_CREDENTIALS`. Iris cannot see your password or reset it.
- **What is a tenant code?** The code of your organisation (tenant) on SafeFare; your administrator gives it to you.
- **Why was I signed out?** The refresh token expired or was revoked, or the tab was closed (sessions live only in that browser tab).
- **Why can't a driver open the admin dashboard?** Drivers hold only `driver.app` and `own.data.read`; Fleet Overview needs `device.read`, so drivers only get My Work.
- **How do I change my password?** See `settings.md` (fleet users) or `driver_my_work.md` → My Profile (drivers).

## 19. Limitations
- NOT VERIFIED: server-side revocation of the refresh token on logout (frontend can't observe it).
- No "forgot password" flow exists in the app.
- Sessions are per browser tab; opening a new tab requires signing in again unless the tab shares storage.
