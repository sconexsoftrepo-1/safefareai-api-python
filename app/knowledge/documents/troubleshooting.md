---
title: Troubleshooting
category: troubleshooting
note: "Separates verified behaviour, known instructions and possible causes. Iris must never claim a specific device, server or integration is faulty without live data."
---

# Troubleshooting

### Why is a device showing offline?
- **Verified meaning:** "Offline" is decided by the SafeFare server — the device is not currently reporting to the GPS vendor.
- **Check (live data):** the device's last `deviceTime`/`receivedAt` (Live Monitoring panel), `batteryPct`, service expiry (`expiresAt`, device detail → Dates & reminders), Fleet Overview device-health counts (Never online, Service expired, Stale > 24 h).
- **Possible causes (unverified for any single device):** ignition/power off, no mobile network or SIM problem, device service expired, never activated, hardware/installation fault.
- **Next step:** if it stays offline, contact the device installer/vendor; Iris cannot diagnose hardware.

### Why am I not receiving notifications?
- **Verified:** the bell count is read only when a page loads and when the panel closes; there is no polling or push in the web app. Reload the page.
- **Possible causes:** the server didn't create a notification for your user for that event (rules not documented); you already read it.

### Why is the dashboard not loading?
- Needs `device.read`; otherwise you see "You don't have access to this page".
- Each widget can fail on its own: 401 → session expired (sign in again); 403 → missing permission for that widget ("No permission for this widget"); 503/502/504 → vendor or database unavailable ("unavailable", retry later); timeout after 15 s.

### Why is a vehicle not appearing?
- Check search text and filters (group, expiry, status, "Without a device").
- **Vehicles** (registry) and **Vehicles & Assets** (devices) are different lists.
- Safe-Fare Admin: check the selected tenant (or "All tenants").
- Records of other organisations always answer 404.
- Known backend issue: a device search with no match may show "unavailable" instead of an empty list.

### Why can't I access a menu?
Your permission set lacks that screen's code (see `roles_permissions.md`). Drivers only get My Work. Settings isn't shown to driver logins. Platform menus need the Safe-Fare Admin. Ask an administrator.

### Why is an alarm missing?
- Different tabs: AI events vs Routine alarms vs Incidents.
- Time range (default Last 7 days) and filters (device, alarm type, Open only).
- GPS provider feed: "unavailable" means the provider or server didn't answer; "No data from vendor" means the provider returned nothing; "Stored data" means an older saved copy is shown.
- Alarm rules (set up by administrators outside the app) may hide some alarm types — NOT VERIFIED per organisation.

### Why is historical video unavailable?
In-app playback is not implemented (vendor SDK/player not provided). You can list recordings and request clip exports. Also check the device is video-capable, the channel, and that the calendar shows recordings for that day.

### Why is my login failing?
- Wrong account type: tenant users need **Tenant user** + tenant code; the platform admin uses **Safe-Fare Admin** without a code.
- 401 `INVALID_CREDENTIALS`: wrong code/login/password.
- Account disabled or locked (too many failed sign-ins) → an admin can **Enable**/**Unlock** in Users & Sub-Accounts.
- Iris can't reset passwords or see credentials.

### Why does a driver get "Your account is not linked to a driver profile"?
The login isn't linked to a driver record. Admin: Drivers → Edit → **Linked user id**.

### Why is a create/edit button missing or disabled?
- Missing permission (e.g. `driver.create`).
- Safe-Fare Admin in "All tenants" mode → select a tenant.
- Feature intentionally disabled: device transfer/delete, new group, send command, geofence create/edit, alert assign.

### What does "No data from vendor" / "Stored data" mean?
The SafeFare server couldn't get fresh data from the GPS provider (GPSTrackTech). "No data from vendor" = the provider returned nothing; "Stored data" = the last saved copy is shown and may be out of date.

### What do error messages mean?
- **Check the highlighted fields** — some values are missing or invalid.
- **Select a tenant first** — the Safe-Fare Admin must pick an organisation before changing records.
- **Session expired** — sign in again.
- **You don't have permission** — your role lacks the permission; ask an administrator.
- **Not found** — the record doesn't exist, was deleted, or belongs to another organisation.
- **Already exists / in use / not allowed now** — e.g. a duplicate vehicle number, a vehicle with a device still fitted, or a status change that isn't allowed.
- **Unavailable** — the GPS provider or the server is temporarily not answering; try again later.
Every error shows a reference code; quote it when reporting the problem.
