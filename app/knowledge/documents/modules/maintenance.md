---
module: Maintenance (reminders)
feature_keys:
- maintenance
- maintenance-reminders
- service-due
- insurance-due
- upcoming-maintenance
routes:
- no dedicated screen — reminders appear on /drive-vision/overview (Upcoming reminders) and device detail (Dates & reminders)
roles:
- users with device.read (dashboard); maintenance.* for the API
permissions:
- maintenance.read
- maintenance.create
- maintenance.update
availability: NOT IMPLEMENTED IN FRONTEND (reminders from device dates only)
technical_reference: api/modules/maintenance_api.md
---

# Maintenance

## 1. What exists
- **In the app:** Fleet Overview → **Upcoming reminders** lists *Service expiry*, *Insurance due* and *Maintenance due* dates taken from each device record, overdue included; the window follows your expiry-reminder setting in Settings. The device detail page shows the same dates under *Dates & reminders*. Insurance/maintenance due dates can be edited in the device **Edit** form.
- **Not in the app:** creating, updating, completing or cancelling maintenance reminders (including mileage-based reminders) is supported by the backend but has no screen.

## 9. Workflow
**When is a vehicle's next maintenance?** Fleet Overview → Upcoming reminders, or Vehicles & Assets → device → Dates & reminders → Next maintenance.

## 18. Common questions
- **Can I create a maintenance reminder?** Not in the app; there is no maintenance screen yet.

## 19. Limitations
No maintenance screen; mileage-based reminders not shown.
