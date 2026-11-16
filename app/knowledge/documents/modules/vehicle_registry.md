---
module: Vehicles (Vehicle Registry)
feature_keys:
- vehicles
- vehicle-registry
- add-vehicle
- register-vehicle
- edit-vehicle
- delete-vehicle
- vehicle-number
- device-fitted
routes:
- /drive-vision/vehicle-registry
roles:
- users with vehicle.read
permissions:
- vehicle.read
- vehicle.create
- vehicle.update
- vehicle.delete
availability: IMPLEMENTED, NOT VERIFIED
technical_reference: api/modules/vehicle_registry_api.md
---

# Vehicles (Vehicle Registry)

## 1. Purpose
The register of the organisation's **vehicles** (bus, van, car…): vehicle number, type, make, model, year, chassis/engine numbers, colour, status, and which tracking **device** is fitted. A vehicle is the physical vehicle; a device is the tracker/camera unit installed in it (see `devices_vehicles_assets.md`).

## 2. Navigation
Sidebar **Monitor → Vehicles**. Subtitle: "Registered vehicles and the tracking device fitted in each".

## 3. Screens
- List with views **All vehicles** / **Without a device**.
- Detail panel (View): Vehicle number, Type, Make, Model, Year, Colour, Chassis number, Engine number, Status, Remarks, Tracking device, Registered, Updated.
- **Register vehicle** / **Edit** form panel; **Delete vehicle** confirmation.

## 5. Buttons
| Button | Permission | What it does |
|---|---|---|
| Register vehicle | vehicle.create (+ selected tenant for Safe-Fare Admin) | Registers the vehicle |
| Edit | vehicle.update | Saves changes (all fields are replaced) |
| Delete → Delete vehicle | vehicle.delete | Deletes the vehicle |
| Refresh | vehicle.read | reload |

## 6. Form fields
| Field | Label | Required | Rule |
|---|---|---|---|
| vehicleNumber | Vehicle number | **yes** | 1–20 chars, stored UPPER-CASE, unique in the organisation (also among deleted vehicles) |
| vehicleType | Type | no | ≤ 50, free text; suggestions BUS, MINI_BUS, VAN, CAR, TRUCK, AMBULANCE |
| make / model | Make / Model | no | ≤ 100 each |
| yearOfManufacture | Year of manufacture | no | 4 digits, 1900 … next year |
| chassisNumber / engineNumber | Chassis number / Engine number | no | ≤ 60, upper-case |
| color | Colour | no | ≤ 30 |
| status | Status | — | Active / Inactive (default Active) |
| remarks | Remarks | no | ≤ 500 |

## 7. Columns and filters
Columns: Vehicle, Type, Colour, Chassis no., Device ("No device" when none), Tenant (all-tenants mode), Status. Filters: **Search vehicles** ("Number, make, model, chassis…"), Status (Any status/Active/Inactive), Type (Any type), Device (Any device / Device fitted / No device).

## 8. Search, sort, paging
Server search (`keyword` matches number, make, model, chassis or engine), sorted by vehicle number, paged (20, max 100).

## 9. Workflows
**How can I add (register) a vehicle?**
1. Monitor → **Vehicles**.
2. (Safe-Fare Admin: select a tenant first.)
3. **Register vehicle** → enter **Vehicle number** (required) and optional details → save.
4. Then fit a tracking device to it (device side; see limitations).
**Deactivate a vehicle**: Edit → Status = Inactive ("the device stays fitted, but no other device can be fitted until the vehicle is active again").
**Delete a vehicle**: View → Delete → **Delete vehicle**. Refused while a device is fitted.

## 10–11. Roles / permissions
`vehicle.read/create/update/delete`. Not offered to drivers.

## 16. Business rules (contract)
- Numbers are case/space-insensitive: "ts09ab1234" = "TS09AB1234".
- PUT replaces all fields; omitted optional fields are cleared; omitted status becomes ACTIVE.
- Delete keeps the number reserved; refused with 409 `RESOURCE_IN_USE` while a device is fitted.
- Admin writes need a tenant (400 `TENANT_REQUIRED`).

## 17. Errors
400 VALIDATION_FAILED / INVALID_VALUE (future year) · 409 DUPLICATE ("A vehicle with this number is already registered") · 409 RESOURCE_IN_USE · 404 NOT_FOUND (unknown, deleted or other organisation's).

## 18. Common questions
- **What is the difference between a vehicle and a device?** Vehicle = the registered bus/van (number plate, make, model). Device = the GPS/camera terminal fitted in it that reports positions, alarms and video. Live data, alarms and video come from devices.
- **How many vehicles are registered?** The Vehicles list total (or ask Iris for the live count).
- **Why can't I delete a vehicle?** A device is still fitted — unlink or delete the device first.
- **What vehicle types can I choose?** Vehicle type is free text (max 50); the form suggests BUS, MINI_BUS, VAN, CAR, TRUCK, AMBULANCE.
- **Which vehicles have no device fitted?** Vehicles → view **Without a device** (or Device filter "No device").

## 19. Limitations / inconsistencies
- The delete hint says "first remove the device from it (edit the device)", but the **device edit form has no vehicle/unlink field** — linking/unlinking a device is NOT IMPLEMENTED in the app.
- Passenger capacity (bus capacity used by Sensors; default 44) is supported by the backend but **not in the vehicle form**.
