---
module: Driver Assignments (driver ↔ vehicle)
feature_keys:
- assign-driver
- driver-assignment
- end-assignment
- replace-assignment
- current-vehicle
routes:
- /drive-vision/drivers (Assign vehicle dialog)
- /drive-vision/vehicles/<deviceId> (Assignment & work panel)
roles:
- users with driver.update to change; driver.read to view
permissions:
- driver.update
- driver.read
- device.read
availability: Read VERIFIED; writes NOT VERIFIED
technical_reference: api/modules/driver_assignments_api.md
---

# Driver Assignments

## 1. Purpose
Record which driver drives which vehicle (device) and when. Assignments are a history; one driver/vehicle should have one active assignment.

## 3. Where
- Drivers → driver drawer → **Assign vehicle**, **Vehicle assignments** list with **End**.
- Device detail (Vehicles & Assets) → *Assignment & work*: Assigned driver, Assignment history (needs `driver.read`).
- Driver app: My Work → Today → Vehicle.

## 6. Assign vehicle form
Vehicle (**required**; picker needs `device.read`), Starts (IST) ("Blank: the server uses the current time"), Ends (IST) ("Optional. Blank: open-ended"; must be after start / in the future), **Replace the current assignment** checkbox. **Review** step shows *Active assignments affected* and requires "Confirm ending the active assignment" when replacing. End assignment: End at (IST) ("Leave blank to end it now").

## 9. Workflow — How can I assign a driver to a vehicle?
1. Fleet → **Drivers** → open the driver.
2. **Assign vehicle**.
3. Choose the **Vehicle**, optional start/end times.
4. If the driver or vehicle already has an active assignment, tick **Replace the current assignment** (otherwise "The server is expected to refuse this…").
5. **Review** → confirm.
To end: open the driver → Vehicle assignments → **End** → optional End at → confirm.

## 16. Business rules
Overlapping assignments are rejected by the server unless **Replace the current assignment** is ticked. Alarms show the driver **as reported by the server**; the app never derives an alarm's driver from the current assignment.

## 18. Common questions
- **What is a driver assignment?** The link between a driver and the vehicle (device) they drive for a period.
- **Which vehicle is assigned to me?** (driver) My Work → Today → Vehicle.

## 19. Limitations
Assign/end actions have not yet been verified against the live server.
