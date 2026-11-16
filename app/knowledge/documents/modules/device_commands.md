---
module: Device Commands
feature_keys:
- commands
- device-commands
- command-history
- command-types
- send-command
routes:
- /drive-vision/devices/commands
roles:
- users with command.send
permissions:
- command.send (even for viewing history)
availability: Read-only; detail blocked; send disabled
technical_reference: api/modules/device_commands_api.md
---

# Device Commands

## 1. Purpose
History of commands sent to devices (e.g. INSTANT_PHOTO, TEXT_MESSAGE, WAKE_UP, OVERSPEED settings) and the catalogue of command types. **Sending is turned off** in this app ("Command history and types from the server — sending is off").

## 2. Navigation
Sidebar **Manage → Device Commands**. Header note "Read-only."

## 3. Screen
**View**: command history / **Command types**. History columns: Command, Status (PENDING, SENT, PARTIAL, SUCCESS, FAILED), Devices, Requested, Completed; filters Type, device; detail: Requested by, Parameters, Targets (per-device status QUEUED/SENT/SUCCESS/FAILED/TIMEOUT). Types list shows "Critical" and "One device at a time" flags.

## 11. Permissions
`command.send` is required even to view history.

## 18. Common questions
- **Can I send a command to a device from SafeFare?** Not from this app; it's disabled until the backend documents the execution contract and charges.

## 19. Limitations
Sending commands and device diagnostics are not available; opening the detail of some commands fails (known backend issue).
