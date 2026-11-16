---
module: Maintenance (reminders)
user_document: documents/modules/maintenance.md
roles:
- users with device.read (dashboard); maintenance.* for the API
permissions:
- maintenance.read
- maintenance.create
- maintenance.update
apis:
- GET /api/v1/maintenance-reminders
- GET /api/v1/maintenance-reminders/upcoming
- GET /api/v1/maintenance-reminders/{id}
- POST /api/v1/maintenance-reminders
- PUT /api/v1/maintenance-reminders/{id}
- POST /api/v1/maintenance-reminders/{id}/cancel
- POST /api/v1/maintenance-reminders/{id}/complete
sources:
- src/components/drive-vision/dashboard/live-dashboard-model.ts
- src/components/drive-vision/dashboard/reminders-list.tsx
- src/components/drive-vision/vehicles/vehicle-detail.tsx
status: NOT IMPLEMENTED IN FRONTEND (API only). Dashboard reminders come from device dates.
---

# Maintenance (reminders) — API and implementation reference

Technical companion of `documents/modules/maintenance.md`. For the Iris tool layer and developers; not for quoting to end users.


## Technical details referenced by the user document

- **In the app:** Fleet Overview → **Upcoming reminders** lists *Service expiry*, *Insurance due* and *Maintenance due* dates taken from each device record (`expiresAt`, `insuranceDueAt`, `maintenanceDueAt`), overdue included; the window follows the user's `expiryReminderDays` preference. The device detail page shows the same dates under *Dates & reminders*. Insurance/maintenance due dates can be edited in the device **Edit** form.
- **In Swagger only (no screen):** maintenance reminders — `ReminderDto` with `reminderType` INSURANCE, SERVICE, MILEAGE, SERVICE_EXPIRY and status OPEN, NOTIFIED, DONE, CANCELLED; create, update, complete, cancel; `/upcoming?withinDays&withinKm&deviceId` (source REMINDER or DEVICE).
