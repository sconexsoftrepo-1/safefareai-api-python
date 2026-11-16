---
module: Device Groups
feature_keys:
- groups
- device-groups
- fleet-groups
- asset-tree
routes:
- /drive-vision/vehicles (Asset tree view, group filter)
- /drive-vision/overview (Fleet groups widget)
roles:
- users with group.read / device.read
permissions:
- group.read
- group.create
- group.update
- group.delete
availability: Read-only
technical_reference: api/modules/device_groups_api.md
---

# Device Groups

## 1. Purpose
Groups organise devices (e.g. by depot, route or customer). They come from the vendor account structure (a group has a name and optional contact email and phone).

## 2–3. Where groups appear
- Vehicles & Assets: **All groups** filter, **Asset tree** view (groups → devices), Group column.
- Live Monitoring: **Group** filter.
- Fleet Overview: **Fleet groups** widget (device count and events per group; needs `group.read`).
- Register device form: **Group** (required).

## 5. Buttons
**New group** on Vehicles & Assets is **disabled** ("…creating groups are disabled until write operations are approved").

## 9. Workflow
**See which devices are in a group**: Vehicles & Assets → View **Asset tree**, or filter **All groups** → choose the group.

## 11. Permissions
`group.read` (list). `group.create/update/delete` exist but no screen uses them.

## 18. Common questions
- **How do I create a group?** Not possible in the app today (disabled pending confirmation of vendor billing side effects).
- **Can I move a device to another group?** No — that's a transfer, which is disabled.

## 19. Limitations
Whether groups limit what a Fleet Owner can see is NOT VERIFIED.
