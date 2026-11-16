---
title: Step-by-step workflows
category: workflows
---

# Step-by-step workflows

Use exact menu names. "Tenant first" = the Safe-Fare Admin must select a tenant in the top-bar tenant switcher before creating or changing records.

### Sign in
1. Open SafeFare → **Sign in**. 2. Account type **Tenant user** (enter **Tenant code**) or **Safe-Fare Admin** (no tenant code). 3. **Email or username**, **Password** → **Sign in**.

### Register (add) a vehicle — `vehicle.create`, tenant first
Monitor → **Vehicles** → **Register vehicle** → Vehicle number (required) + Type, Make, Model, Year, Chassis, Engine, Colour, Status, Remarks → save.

### Register a tracking device — `device.create`, tenant first
Fleet → **Vehicles & Assets** → **Add vehicle** → Name, Device ID (terminal no., 11–20 letters/digits), Group, Device model, Protocol, Object type, Cameras → save → accept the charge message if the server asks.

### Check device status — `device.read`
Fleet → **Vehicles & Assets** → search → **View** → *Latest reported state* (device time, position) and *Dates & reminders*. Online/offline totals: **Fleet Overview** tiles. Report age: **Live Monitoring**.

### Add a driver — `driver.create`, tenant first
Fleet → **Drivers** → **New driver** → Full name (+ licence, contact…) → save.

### Assign a driver to a vehicle — `driver.update`
Fleet → **Drivers** → open driver → **Assign vehicle** → Vehicle, Starts/Ends (IST, optional) → tick **Replace the current assignment** if needed → **Review** → confirm.

### Give a driver app access — `user.create` + `driver.update`
Administration → **Users & Sub-Accounts** → **New user** with role **DRIVER** → note the user id → Fleet → **Drivers** → Edit driver → **Linked user id** → save.

### Create a dispatch — `dispatch.create`
Fleet → **Dispatch** → **New dispatch** → Title, Driver, Vehicle, Scheduled start/end → **Check conflicts** → save → confirm.

### Approve a swap request — `dispatch.update`
Fleet → **Dispatch** → View **Swap requests** → **Approve**/**Reject** (note optional).

### Approve a leave request — `workforce.update`
Fleet → **Workforce** → **Leave** → pending request → **Approve**/**Reject** → confirm.

### Check today's trips — `track.read`
Monitor → **Trips & Tracking** → View **Trips** → Date range **Today** → (vehicle) → select a trip for its route.

### Replay a vehicle's route — `track.read`
Trips & Tracking → View **Track playback** → device → time range (24 h / 3 days / 7 days / Custom) → play. Or Live Monitoring → device → **Track history**.

### View AI alarms / routine alarms — `alarm.read`
Safety → **Alerts & Events** → **AI events** or **Routine alarms** → Time range → filters → row for evidence.

### Handle an alert — `alarm.handle`
Alerts & Events → **Incidents** → open alert → **Acknowledge** → **Comment** → **Resolve** (choose Outcome) or **Dismiss**; **Reopen** if needed.

### Check a driver's safety score — `alarm.read`
Fleet → **Drivers** → open driver → Safety panel; or Safety → **Safety Analytics** → Safety scores → Drivers.

### View historical video — `video.playback`
Monitor → **Historical Video** → Device → (Channel) → calendar day → Recordings → **Export clip → Request export** → **Download** when ready. (In-app playback not available yet.)

### Generate a report — `report.read`
Monitor → **Reports** → Mileage/Driving/Parking/Media → time range → device. (No download button.)

### See geofence events — `geofence.read`
Manage → **Geofences** → select geofence → Geofence events → range/type.

### Create a user — `user.create`, tenant first
Administration → **Users & Sub-Accounts** → **New user** → Display name, Email, Phone, Initial password, Locale, Time zone, Role → save.

### Change my password
Fleet users: Administration → **Settings** → **Change password**. Drivers: My Work → **My Profile** → Change password.

### Work inside a tenant (Safe-Fare Admin)
Top bar tenant switcher → pick tenant → "Working in …". **All tenants** to go back.

### Create a tenant (Safe-Fare Admin)
Platform → **Tenants** → **Create tenant** → name, code (optional), time zone, status, S3 prefix → **Review** → confirm.

### Give a role a permission (Safe-Fare Admin)
Platform → **Global Roles** → role → Permissions → tick → Review changes → save; or Platform → **Permission Catalogue** → Role permissions.

### Driver's day (My Work)
1. **My Shifts** → **Start shift** (odometer optional). 2. **Shift Checklist** → Start checklist → Pass/Fail each item → submit. 3. **My Work** → trip → **Accept** → **Start trip** → **Complete trip**. 4. **My Shifts** → **End shift**. Leave: **My Leave** → **Request leave**.
