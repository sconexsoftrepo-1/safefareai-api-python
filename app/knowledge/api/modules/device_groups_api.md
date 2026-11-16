---
module: Device Groups
user_document: documents/modules/device_groups.md
roles:
- users with group.read / device.read
permissions:
- group.read
- group.create
- group.update
- group.delete
apis:
- GET /api/v1/groups
sources:
- src/components/drive-vision/vehicles/vehicles-page.tsx
- src/components/drive-vision/dashboard/fleet-groups.tsx
- src/components/drive-vision/vehicles/vehicle-dialogs.tsx
status: READ-ONLY. Group create/edit/delete NOT IMPLEMENTED (button disabled).
---

# Device Groups — API and implementation reference

Technical companion of `documents/modules/device_groups.md`. For the Iris tool layer and developers; not for quoting to end users.

## 13. APIs
Used: `GET /groups`. Unused: `POST /groups`, `GET/PUT/DELETE /groups/{id}`.

## Technical details referenced by the user document

- Groups organise devices (e.g. by depot, route or customer). They come from the vendor account structure (`GroupDto {id, vendorGroupId, name, email, phone, syncedAt}`).
- **New group** on Vehicles & Assets is **disabled** ("…creating groups are disabled until write operations are approved"). `NewGroupDialog` in `vehicle-dialogs.tsx` is an unused sample-data dialog.
- `GroupDto` has no owner field; whether groups scope a Fleet Owner's data is NOT VERIFIED.
