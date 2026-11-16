---
module: Devices ("Vehicles & Assets")
user_document: documents/modules/devices_vehicles_assets.md
roles:
- users with device.read
permissions:
- device.read
- device.create
- device.update
- device.delete (unused)
- driver.read (assignment panel)
- alarm.read (events)
apis:
- GET /api/v1/devices
- GET /api/v1/devices/{id}
- POST /api/v1/devices
- PUT /api/v1/devices/{id}
- GET /api/v1/devices/{id}/summary
- GET /api/v1/devices/{id}/driver-assignments
- GET /api/v1/monitor/realtime
- GET /api/v1/groups
- GET /api/v1/reference/device-models
- GET /api/v1/reference/protocols
- GET /api/v1/reference/object-types
- GET /api/v1/trips
- GET /api/v1/alarms/ai
- GET /api/v1/alarms/routine
sources:
- src/app/drive-vision/vehicles/page.tsx
- src/app/drive-vision/vehicles/[vehicleId]/page.tsx
- src/app/drive-vision/vehicles/new/page.tsx
- src/components/drive-vision/vehicles/vehicles-page.tsx
- src/components/drive-vision/vehicles/vehicle-detail.tsx
- src/components/drive-vision/vehicles/vehicle-operations.tsx
- src/components/drive-vision/vehicles/device-create-panel.tsx
- src/components/drive-vision/vehicles/device-create-model.ts
- src/components/drive-vision/vehicles/device-edit-panel.tsx
- src/components/drive-vision/vehicles/device-edit-model.ts
- src/components/drive-vision/vehicles/use-fleet-reference.ts
- src/features/drive-vision/api/fleet-service.ts
server_menu_key: vehicles_assets
status: List/detail VERIFIED LIVE (2026-10-26/29). Register device and edit IMPLEMENTED, NOT VERIFIED. Transfer, delete and New group DISABLED.
---

# Devices ("Vehicles & Assets") — API and implementation reference

Technical companion of `documents/modules/devices_vehicles_assets.md`. For the Iris tool layer and developers; not for quoting to end users.

## 13–15. APIs
`GET /devices?groupId&keyword&pageNumber&pageSize` → `[DeviceDto {id, vendorVehicleId, vehicleId, groupId, name, terminalNo, modelId, protocolCode, objectTypeId, plateColor, simNumber, cameraCount, cameraLines, frameNo, remark, activatedAt, expiresAt, insuranceDueAt, maintenanceDueAt, driver, terminal, …, syncedAt}]`. `POST/PUT /devices` body `DeviceRequest`. `GET /devices/{id}/summary`.

## Technical details referenced by the user document

- Sidebar **Fleet → Vehicles & Assets** (`/drive-vision/vehicles`). Detail: `/drive-vision/vehicles/<deviceId>`. `/drive-vision/vehicles/new` redirects to the list with the add panel open.
| Add vehicle | enabled with `device.create` (+ selected tenant) | Opens *Register device* → `POST /devices` |
| Edit (detail) | enabled with `device.update` (+ tenant) | `PUT /devices/{id}` (full replace, locked fields resent unchanged) |
- **Register device** (`device-create-model.ts`):
| Device model | yes | from `/reference/device-models` |
| Object type | yes | from `/reference/object-types` |
- **Why is a vehicle not appearing?** Check filters/search; the device may belong to another tenant (Safe-Fare Admin: check the selected tenant); a "no match" search may wrongly return 503 (backend defect #13).
- **Why is a vehicle/device not appearing in the Vehicles & Assets list?** Check the search text and the group/expiry filters; the device may belong to another tenant (Safe-Fare Admin: check the selected tenant); a search with no match may answer 503 instead of an empty list (backend defect #13).
- Transfer (`POST /devices/transfer`), delete (`DELETE /devices/{id}`) and group creation not available.
- Fitting a device into a registered vehicle (`vehicleId`, `unlinkVehicle` in `DeviceRequest`) is NOT IMPLEMENTED in the forms.
- `GET /assets/tree` (Swagger) is unused; the asset tree is built from groups + devices.
