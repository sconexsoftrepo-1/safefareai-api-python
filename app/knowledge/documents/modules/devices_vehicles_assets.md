---
module: Devices ("Vehicles & Assets")
feature_keys:
- devices
- vehicles-and-assets
- tracking-device
- terminal
- register-device
- edit-device
- device-detail
- asset-tree
- device-status
routes:
- /drive-vision/vehicles
- /drive-vision/vehicles/<deviceId>
- /drive-vision/vehicles/new (redirects to /drive-vision/vehicles?add=1)
roles:
- users with device.read
permissions:
- device.read
- device.create
- device.update
- device.delete (unused)
- driver.read (assignment panel)
- alarm.read (events)
availability: Read VERIFIED; create/edit NOT VERIFIED; transfer/delete disabled
technical_reference: api/modules/devices_vehicles_assets_api.md
---

# Devices — "Vehicles & Assets"

## 1. Purpose
Manage the **tracking devices** (GPS/MDVR/camera terminals) registered with SafeFare and the GPS vendor (GPSTrackTech): list, group, view live state, register new devices and edit descriptive fields. Despite the menu name "Vehicles & Assets", every row is a **device**; the separate **Vehicles** menu is the vehicle registry.

## 2. Navigation
Sidebar **Fleet → Vehicles & Assets**. Open a row with **View** for the device detail page.

## 3. Screens
- **List** with **View**: *Vehicle list* (table) or *Asset tree* ("Groups and devices").
- **Device detail**: header buttons Transfer (disabled), Delete (disabled), **Edit**; panels *Latest reported state* (map position, raw codes), *Device & SIM* (Device ID, Protocol, Object type, Cameras, Frame / VIN, Plate colour, Last vendor sync), *Dates & reminders* (Activated, Service expiry, Insurance due, Next maintenance), *Driver — Stored on the device record* (Name, Phone, Card, Licence, Remark), *Recent events* (AI events and routine alarms, last N days), *Assignment & work* (Status, Assigned driver, Open alerts, Current dispatch, Assignment history), *Recent trips*.
- **Register device** panel (button label **Add vehicle**) and **Edit** panel.

## 5. Buttons
| Button | State | What it does |
|---|---|---|
| Add vehicle | enabled with `device.create` (+ selected tenant) | Opens *Register device* and registers the device |
| Edit (detail) | enabled with `device.update` (+ tenant) | Saves the editable fields (locked fields stay unchanged) |
| New group | **disabled** — "Moving and deleting devices and creating groups are disabled until write operations are approved." |
| Transfer, Delete (detail) | **disabled**, same reason |
| Clear filters | resets filters |

## 6. Form fields
**Register device**:
| Field | Required | Rule |
|---|---|---|
| Name | yes | "Enter a device name." ≤ 100 |
| Device ID (terminal no.) | yes | 11–20 letters/digits, no spaces (`^[0-9A-Za-z]{11,20}$`) |
| Group | yes | choose from groups |
| Device model | yes | from the server's list of models |
| Protocol | yes | 1–3 (model's own list) |
| Object type | yes | from the server's list |
| Cameras | yes | 0–16 |
| Plate colour, SIM number, Frame/VIN, Remark, Insurance due, Maintenance due, Driver (name, card, phone, licence, remark) | no | max lengths (plateColor 30, simNumber 30, frameNo 60, remark 500, driverName 150, driverCard 60, …) |
Chargeable change: if the server answers `CHARGEABLE_CHANGE` / `CONFIRMATION_REQUIRED`, the panel shows the server's message and the user must tick "I accept this and want to register the device" → resend with `confirmChargeableChange: true`.

**Edit device**: only descriptive fields (name, plate colour, SIM, frame no, remark, insurance/maintenance due, driver name/card/phone/licence/remark). Locked and resent unchanged: model ("may deduct vendor coins"), protocol, camera count, terminal number, group (a move = transfer), object type, driver gender.

## 7. Table columns and filters
Columns: Vehicle (device name), Model, Type, Group, Driver ("Not recorded"), Last report, Cams, Service expiry. Filters: **Search vehicles** ("Name or device ID"), **All groups**, expiry (Any expiry · Expiring ≤ 30 d · Expired).

## 9. Workflows
**How can I check device status?** Vehicles & Assets → search the device → **View** → *Latest reported state* (device time, received time, position, raw status codes) and *Dates & reminders* (service expiry). For connectivity use Live Monitoring (report age) or Fleet Overview (online/offline server counts).
**Register a new tracking device**: Vehicles & Assets → **Add vehicle** → fill required fields → save → if asked, accept the charge message.

## 10–11. Roles / permissions
`device.read` (screen); `device.create`; `device.update`; detail assignment panel needs `driver.read`; events need `alarm.read`.

## 16. Business rules
- Registering also registers the device at the GPS vendor; vendor timeouts (502/504, `VENDOR_OUTCOME_UNKNOWN`) mean "may or may not have been registered — check the list before retrying".
- The driver stored **on the device record** is vendor data; it is not the same as a driver assignment (Drivers screen).
- Undocumented codes (statusCode, positionMode, networkType) are displayed raw, never interpreted.

## 17. Errors
409 `DUPLICATE` → "This terminal number is already registered"; 400 `TENANT_REQUIRED` → "Select a tenant first"; field errors per field.

## 18. Common questions
- **What is a device?** The tracking/camera unit (terminal) identified by its Device ID (terminal no.), reporting GPS, alarms and video.
- **What is a device group?** A folder of devices (fleet group) used for filtering and permissions at the vendor; see `device_groups.md`.
- **Why can't I move or delete a device?** Transfer and delete are disabled until the backend documents charges/side effects.
- **Why is a vehicle not appearing?** Check filters/search; the device may belong to another tenant (Safe-Fare Admin: check the selected tenant); a search with no match may show "unavailable" instead of an empty list (known backend issue).
- **What format is the device ID (terminal number)?** 11–20 letters or digits with no spaces (`^[0-9A-Za-z]{11,20}$`).
- **Why is a vehicle/device not appearing in the Vehicles & Assets list?** Check the search text and the group/expiry filters; the device may belong to another tenant (Safe-Fare Admin: check the selected tenant); a search with no match may show "unavailable" instead of an empty list (known backend issue).

## 19. Limitations
- Moving (transfer) and deleting devices and creating groups are not available.
- Linking a device to a registered vehicle (or unlinking it) is NOT IMPLEMENTED in the forms.
