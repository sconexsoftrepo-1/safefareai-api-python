---
module: Drivers
feature_keys:
- drivers
- driver-records
- licence
- licence-expiry
- driver-safety-score
- create-driver
- edit-driver
- delete-driver
- linked-user
routes:
- /drive-vision/drivers
- /drive-vision/drivers?driver=<id>
roles:
- users with driver.read
permissions:
- driver.read
- driver.create
- driver.update
- driver.delete
- alarm.read (safety panel)
- device.read (vehicle picker)
availability: Read VERIFIED; writes NOT VERIFIED
technical_reference: api/modules/drivers_api.md
---

# Drivers

## 1. Purpose
Driver records (contact, licence, employment), licence expiry tracking, vehicle assignments and each driver's server-computed safety score.

## 2. Navigation
Sidebar **Fleet → Drivers**.

## 3. Screens
- **View**: *Drivers* list or *Licence expiries* (Window: Within 30 / 60 / 90 days).
- Driver drawer: Status, Licence, Current vehicle, Phone, Email, IC card, Emergency contact, Hired, Linked user, Remark, Updated; **Safety** (Score, Alarms · severe, Distance — last 30 days); **Vehicle assignments** history.
- Create/Edit form; Assign vehicle dialog (see `driver_assignments.md`); Delete confirmation.

## 5. Buttons
| Button | Permission | What it does |
|---|---|---|
| New driver | driver.create (+tenant) | Creates the driver |
| Edit | driver.update | Saves changes |
| Delete | driver.delete | Deletes the driver |
| Assign vehicle / End | driver.update | Creates or ends a vehicle assignment |
| Refresh | driver.read | reload |

## 6. Form fields
Full name (**required**, ≤150), Licence number (≤60), Licence class (≤30), Licence issued, Licence expires (date ≥ issued), IC card number (≤60), Phone (≤30), Email (valid, ≤320), Address (≤500), Date of birth, Emergency contact (≤150), Emergency phone (≤30), Hired on, Remark (≤500), Gender (Not set / values), Status (Active / Inactive), **Linked user id** (numeric; "Optional login account for driver self-service"). Dates YYYY-MM-DD. "Licence status and days to expiry are calculated by the server from the expiry date."

## 7. Columns and filters
Driver, Licence (status VALID / EXPIRING / EXPIRED / MISSING), Assignment (vehicle or "Unassigned"), Phone, Email, Tenant (all-tenants mode), Status. Filters: **Search drivers** (keyword, debounced), Status (Any status / Active / Inactive). Server paging.

## 9. Workflows
**Add a driver**: Drivers → **New driver** → Full name (+ details) → save.
**Give a driver app access**: create a user with the DRIVER role in Users & Sub-Accounts, then edit the driver and set **Linked user id** to that user's id.
**Check a driver's safety score**: Drivers → open the driver → Safety panel (last 30 days). Or Safety Analytics → Safety scores → Drivers.
**Licences expiring soon**: View **Licence expiries** → Window 30/60/90 days.

## 10–11. Roles / permissions
`driver.read` screen; writes as above. Drivers themselves use My Work, not this screen.

## 16. Business rules
The linked user is only shown for information. Safety data comes only from the server.

## 17. Errors
Server field errors shown per field; an unknown driver shows "not found".

## 18. Common questions
- **What is a driver?** A person who drives fleet vehicles, stored as a driver record; optionally linked to a login so they can use My Work.
- **How many drivers are assigned?** Drivers list → Assignment column, or ask Iris (live data).
- **Which drivers have expiring licences?** View Licence expiries.
- **What licence statuses exist?** Licence status values: VALID, EXPIRING, EXPIRED, MISSING (computed by the server from the expiry date).

## 19. Limitations
Writes not verified live. Delete cascade behaviour NOT VERIFIED.
