---
module: Vehicles (Vehicle Registry)
user_document: documents/modules/vehicle_registry.md
roles:
- users with vehicle.read
permissions:
- vehicle.read
- vehicle.create
- vehicle.update
- vehicle.delete
apis:
- GET /api/v1/vehicles
- GET /api/v1/vehicles/available
- GET /api/v1/vehicles/{id}
- POST /api/v1/vehicles
- PUT /api/v1/vehicles/{id}
- DELETE /api/v1/vehicles/{id}
sources:
- src/app/drive-vision/vehicle-registry/page.tsx
- src/components/drive-vision/vehicle-registry/vehicle-registry-page.tsx
- src/components/drive-vision/vehicle-registry/vehicle-registry-model.ts
- src/features/drive-vision/api/vehicle-registry-service.ts
- docs/contracts/vehicle-api.txt
server_route_paths:
- /vehicle-registry
server_menu_key: vehicles
status: IMPLEMENTED (contract docs/contracts/vehicle-api.txt, 2026-11-03; now in provided Swagger). Live use NOT VERIFIED in repo evidence.
---

# Vehicles (Vehicle Registry) — API and implementation reference

Technical companion of `documents/modules/vehicle_registry.md`. For the Iris tool layer and developers; not for quoting to end users.

## 13–15. API
See front matter and `api_reference.md`. `VehicleDto {id, vehicleNumber, vehicleType, make, model, yearOfManufacture, chassisNumber, engineNumber, color, status ACTIVE|INACTIVE, remarks, passengerCapacity, deviceAssigned, device {id,name,terminalNo}, createdAt, updatedAt}`; list rows also carry tenantId, tenantName. `GET /vehicles/available` = ACTIVE vehicles with no device (for device forms).

## Technical details referenced by the user document

- Sidebar **Monitor → Vehicles** (`/drive-vision/vehicle-registry`). Server menu key `vehicles`, routePath `/vehicle-registry`. Subtitle: "Registered vehicles and the tracking device fitted in each".
| Register vehicle | vehicle.create (+ selected tenant for Safe-Fare Admin) | `POST /vehicles` |
| Edit | vehicle.update | `PUT /vehicles/{id}` (full replace) |
| Delete → Delete vehicle | vehicle.delete | `DELETE /vehicles/{id}` |
- **How many vehicles are registered?** The Vehicles list total (or ask Iris, which calls `GET /vehicles`).
- **Which vehicles have no device fitted?** Vehicles → view **Without a device** (or Device filter "No device"). `GET /vehicles?assigned=false`; `GET /vehicles/available` lists ACTIVE vehicles without a device.
- The delete hint says "first remove the device from it (edit the device)", but the **device edit form has no vehicle/unlink field** — fitting/unlinking (`vehicleId`, `unlinkVehicle` on `PUT /devices/{id}`) is NOT IMPLEMENTED in the frontend.
- `passengerCapacity` (bus capacity used by Sensors; default 44) is in the Swagger `VehicleDto` and contract but **not in the vehicle form**.
