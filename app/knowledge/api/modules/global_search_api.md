---
module: Global Search
user_document: documents/modules/global_search.md
roles:
- all users for page search; record search needs device.read
permissions:
- device.read (record search)
apis:
- GET /api/v1/search
sources:
- src/components/drive-vision/app-shell/global-search.tsx
- src/components/drive-vision/app-shell/search-model.ts
status: VERIFIED LIVE 2026-10-29
---

# Global Search — API and implementation reference

Technical companion of `documents/modules/global_search.md`. For the Iris tool layer and developers; not for quoting to end users.


## Technical details referenced by the user document

- Starts after 2 characters, 300 ms debounce, `GET /search?q&limit=8`. Results grouped by type; linked only when you can open the target screen. Drivers get page results only.
