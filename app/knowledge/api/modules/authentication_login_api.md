---
module: Authentication and Sign-in
user_document: documents/modules/authentication_login.md
roles:
- Safe-Fare Admin
- Tenant ADMIN
- Fleet Owner
- Driver
- any tenant user
permissions:
- none (public) for login/refresh
- any signed-in user for logout/me
apis:
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout
- GET /api/v1/me
- GET /api/v1/me/permissions
- GET /api/v1/me/menus
sources:
- src/app/login/page.tsx
- src/components/drive-vision/auth/login-screen.tsx
- src/components/drive-vision/auth/login-model.ts
- src/components/drive-vision/auth/auth-gate.tsx
- src/components/drive-vision/auth/route-guard.tsx
- src/features/drive-vision/api/auth-service.ts
- src/features/drive-vision/api/session.ts
- src/features/drive-vision/api/client.ts
- src/features/drive-vision/access/identity.ts
status: VERIFIED LIVE (login, refresh, logout, /me — docs/feature-status.md, 2026-10-26/27)
---

# Authentication and Sign-in — API and implementation reference

Technical companion of `documents/modules/authentication_login.md`. For the Iris tool layer and developers; not for quoting to end users.

## 12. Frontend files
See front matter. Access resolution: `src/features/drive-vision/access/access-policy.ts` (`computeAccess`, `defaultLanding`).
## 13–15. API, payloads, responses
- `POST /api/v1/auth/login` body `LoginRequest {tenantCode?, login, password}` → `TokenResponse {accessToken, tokenType, expiresIn, refreshToken, refreshExpiresIn, user: CurrentUserDto, menus[]}`.
- `POST /api/v1/auth/refresh` body `{refreshToken}` → same `TokenResponse`.
- `POST /api/v1/auth/logout` — in practice requires the bearer token (401 without it, observed 2026-10-27).
- `GET /api/v1/me` → `CurrentUserDto {id, tenantId, tenantCode, tenantName, platform, displayName, email, phone, locale, timezone, parentUserId, role {id, code, description}, permissions[], lastLoginAt}`.
- `GET /api/v1/me/permissions` → `MyPermissionsDto {userId, platform, homeTenantId, tenantId, roleId, roleCode, permissions[], screens[]}`.

## Technical details referenced by the user document

- Sign-in page: `/login` (`src/app/login/page.tsx`). `/` and protected routes redirect here when there is no session, with `?next=<path>` so the user returns to the page they wanted.
- Sign-out: avatar/profile menu in the top bar → **Sign out** (`app-shell/user-profile-menu.tsx`). The access-denied panel also offers **Sign out**.
- "Couldn't load your session" panel with **Try again** (auth gate) when `/me` fails.
- Session tokens kept in the browser tab's `sessionStorage` (cleared when the tab closes, survives reload).
- Automatic, cross-tab-safe token refresh before expiry (`client.ts`, `session-sync.ts`).
- Identity from `GET /me/permissions` (permissions, platform flag, role code, server screens) drives navigation and route guards.
| Sign in | `POST /auth/login`. |
| Sign out | `POST /auth/logout` (sends bearer token + refresh token), then clears the session. |
| Try again | Re-reads the session (`/me`). |
| tenantCode | Tenant code | Tenant user: yes. Safe-Fare Admin: not shown, never sent | 50 | Can be pre-filled from `NEXT_PUBLIC_DEFAULT_TENANT_CODE`. |
- Login and refresh are public. Logout, `/me`, `/me/permissions`, `/me/menus` need only a signed-in user.
- `tenantCode` is sent only for a tenant sign-in with a non-blank code; never as "" or null.
- `/me` failure → "Couldn't load your session" + **Try again**.
- Sessions are per browser tab (sessionStorage); opening a new tab requires signing in again unless the tab shares storage.
