---
module: Features not available in the app
feature_keys:
- not-available
- missing-features
- alarm-rules
- report-schedules
- report-export
- audit-log
- renewals
- maintenance-reminders
- device-transfer
- send-command
- geofence-create
- user-delete
- tenant-edit
roles:
- all
permissions: []
availability: NOT IMPLEMENTED IN FRONTEND
technical_reference: api/modules/features_not_in_app_api.md
---

# Features not available in the app

Iris must **not** give screen steps for these. The SafeFare backend supports most of them, but there is no screen (or the button is disabled) in the current app. Say clearly that the feature isn't available yet, and suggest contacting the SafeFare administrator if it is needed.

| Feature | Situation in the app |
|---|---|
| Alarm rules (choose how each alarm type is handled: hide, display only, process, high priority) | No screen |
| Report schedules (send reports automatically as CSV/XLSX/PDF) | No screen |
| Report download / export, idle report | No button / no tab |
| Audit log | No screen |
| Vendor (GPSTrackTech) user accounts | Deliberately not offered (vendor side effects) |
| Device service renewals | Deliberately not offered (uses vendor credit) |
| Uploading voice files | No screen (geofence voice prompts are view-only) |
| Menu administration, menu permissions per role | No screen |
| Mobile push notifications | Not in the web app |
| Changing alarm type settings | No screen |
| Moving (transferring) or deleting devices, creating groups | Buttons disabled |
| Creating, editing or deleting trips | No screen (trips are detected automatically) |
| Deleting users | Not offered (disable instead) |
| Editing, suspending or deleting tenants | No screen |
| In-app video playback | Not available (export clips instead) |
| Safety heatmap, false-positive analysis, fleet health page | Not shown |
| Device diagnostics | Not shown |
| Maintenance reminders (create, complete, cancel) | No screen |
| Creating or editing geofences | Blocked |
| Sending commands to devices | Disabled |
| Assigning an alert to a person | Not available |
| Forgot-password self-service | Not available (an admin can reset passwords) |
| Native driver mobile app | Not in the project (drivers use My Work in the browser) |
