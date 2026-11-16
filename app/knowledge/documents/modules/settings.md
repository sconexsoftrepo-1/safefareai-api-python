---
module: Settings (profile, password, preferences)
feature_keys:
- settings
- profile
- change-password
- preferences
- workspace-preferences
- video-layout
- expiry-reminders
- night-mode
routes:
- /drive-vision/settings
roles:
- all signed-in fleet users (not driver logins)
permissions:
- any signed-in user (non-empty permission set)
availability: VERIFIED LIVE (profile, prefs)
technical_reference: api/modules/settings_api.md
---

# Settings

## 1. Purpose
Your own account: profile details, password, server-saved workspace preferences and browser-only display options.

## 2. Navigation
Sidebar **Administration → Settings**. Not shown to driver logins (drivers use My Work → My Profile).

## 3. Sections
1. **Profile** — "Your account details on the SafeFare server": Display name, Email, Phone, Locale, Time zone, Tenant (read-only). **Save** / **Discard**.
2. **Change password** — "Takes effect on the server; other sessions may need to sign in again".
3. **Workspace preferences** — "Saved to your account on the SafeFare server": Video layout (GRID_1, GRID_4, GRID_9, GRID_16), auto-stop, Expiry reminders (NONE, BADGE, POPUP_AND_BADGE) and reminder days, alarm pop-up limits, Cluster map markers, Night mode.
4. **This browser** — "stored on this device only": Reduce motion, Show AI assistant (Iris launcher), Overview cards.

## 6. Validation
Profile: Display name required (≤150), Email valid (≤320), Phone 5–30 (digits, spaces, + ( ) -), Locale like en or en_IN, Time zone ≤50. Password: Current password required; New password required (≤72) and different from current; Confirm must match. No strength rule is documented.

## 9. Workflows
**How do I change my password?** Settings → **Change password** → current password, new password, confirm → save. (Drivers: My Work → **My Profile** → Change password.)
**Update my phone number**: Settings → Profile → Phone → Save.

## 16. Business rules
Profile saves only the fields you changed. Some stored preferences (theme, home modules, device info fields, track alarm types) can't be edited here and are kept as they are.

## 18. Common questions
- **I forgot my password.** There is no self-service reset; ask an administrator to use Users & Sub-Accounts → Reset password.

## 19. Limitations
The language preference is stored but the app is not translated yet. Clearing optional profile fields not supported.
