---
title: Known limitations
category: limitations
---

# Known limitations

## What the app can't do yet
Iris must say these aren't available, not invent steps. Full list: `modules/features_not_in_app.md`.

| Feature | Situation |
|---|---|
| Historical video playback | Not available (the video provider's player hasn't been supplied). Clips can be exported and downloaded. |
| Report download / export, report schedules | No button or screen. |
| Moving or deleting devices, creating device groups | Buttons disabled until the backend confirms costs and side effects. |
| Linking or unlinking a device to a registered vehicle | Not in the forms. |
| Bus passenger capacity on vehicles | Not in the vehicle form (Sensors uses 44 by default). |
| Creating or editing geofences | Blocked until rule codes are documented. |
| Sending commands to devices | Disabled. |
| Assigning an alert to a person | Not available yet. |
| Deleting users | Not offered (disable instead). Roles are edited only by the Safe-Fare Admin in Global Roles. |
| Maintenance reminders, alarm rules, audit log, renewals, voice upload, menu admin | No screen. |
| Forgot password | No self-service; an administrator resets passwords. |
| Native driver mobile app | Not part of the project; drivers use My Work in the browser. |
| Online/offline filter on Live Monitoring | Not present; the Offline tile on Fleet Overview opens Live Monitoring unfiltered. |
| Automatic notification updates | The bell refreshes only on page load or when the panel closes. |

## Things that may confuse users
- **Vehicles** (registered vehicles) and **Vehicles & Assets** (tracking devices) are different menus; the device register button is labelled **Add vehicle**.
- Vehicles: the delete message says to remove the device by editing it, but the device form has no such option.
- The "Fleet Owner" role name isn't confirmed by the backend yet; what a user can do depends on the permissions of their role.
- Severity values and some device status codes are shown exactly as the server sends them; their scale is not documented.
- Live data has been verified only with a small test organisation; create/edit/delete actions have not been verified against the live server.
