---
module: Device Commands
user_document: documents/modules/device_commands.md
roles:
- users with command.send
permissions:
- command.send (even for viewing history)
apis:
- GET /api/v1/commands
- GET /api/v1/commands/{id}
- GET /api/v1/commands/types
sources:
- src/app/drive-vision/devices/commands/page.tsx
- src/components/drive-vision/devices/device-commands.tsx
- src/components/drive-vision/devices/commands-model.ts
status: 'History and types VERIFIED LIVE 2026-10-27; detail BLOCKED (GET /commands/{id} → 500, #28); SEND NOT IMPLEMENTED (disabled)'
---

# Device Commands — API and implementation reference

Technical companion of `documents/modules/device_commands.md`. For the Iris tool layer and developers; not for quoting to end users.


## Technical details referenced by the user document

- Sidebar **Manage → Device Commands** (`/drive-vision/devices/commands`). Header note "Read-only."
- `POST /commands` unused; `GET /devices/{id}/passthrough-data` (diagnostics) not integrated; command detail 500 for some records (#28).
