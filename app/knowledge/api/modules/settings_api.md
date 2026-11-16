---
module: Settings (profile, password, preferences)
user_document: documents/modules/settings.md
roles:
- all signed-in fleet users (not driver logins)
permissions:
- any signed-in user (non-empty permission set)
apis:
- GET /api/v1/me
- PATCH /api/v1/me
- POST /api/v1/me/password
- GET /api/v1/me/preferences
- PUT /api/v1/me/preferences
sources:
- src/app/drive-vision/settings/page.tsx
- src/components/drive-vision/settings/settings-page.tsx
- src/components/drive-vision/settings/settings-model.ts
- src/features/drive-vision/api/account-service.ts
status: Profile PATCH and preferences PUT VERIFIED LIVE (round-trip 2026-10-27); change password IMPLEMENTED, NOT VERIFIED
---

# Settings (profile, password, preferences) — API and implementation reference

Technical companion of `documents/modules/settings.md`. For the Iris tool layer and developers; not for quoting to end users.


## Technical details referenced by the user document

- Sidebar **Administration → Settings** (`/drive-vision/settings`). Not shown to driver logins (drivers use My Work → My Profile).
- PATCH /me sends only changed fields. PUT /me/preferences sends the whole loaded object (full replace). Theme, home modules, device info fields and track alarm types are kept as stored (values undocumented).
- Language preference stored but UI not translated (README). Clearing optional profile fields not supported (Q7).
