---
module: Driver application — My Work (driver self-service)
feature_keys:
- driver-app
- my-work
- my-trips
- accept-trip
- start-trip
- complete-trip
- decline-trip
- my-shift
- start-shift
- end-shift
- working-hours
- my-leave
- checklist
- my-safety
- my-profile
- driver-mobile
routes:
- /drive-vision/my-work
- /drive-vision/my-work/shifts
- /drive-vision/my-work/leave
- /drive-vision/my-work/checklist
- /drive-vision/my-work/safety
- /drive-vision/my-work/profile
roles:
- Driver (role DRIVER, not platform) linked to a driver profile
permissions:
- driver.app
- own.data.read
availability: Read VERIFIED (Driver); writes NOT VERIFIED
technical_reference: api/modules/driver_my_work_api.md
---

# Driver application — My Work

## 1. Purpose
Self-service for drivers: today's vehicle and trips, accept/start/complete trips, shifts and working hours, leave, pre-trip checklist, own safety score and profile. NOT VERIFIED: a separate native "driver mobile app" — none is in the provided project; My Work is the driver app inside the web UI (mobile-friendly).

## 2. Navigation (sidebar built from the server's driver menus)
| Page | Description |
|---|---|
| My Work (Today) | Today, current/next trip, upcoming trips |
| My Shifts | "Your current shift and working hours" |
| My Leave | "Your leave requests and their status" |
| Shift Checklist | "Pre-trip vehicle checklist and your recent submissions" |
| My Safety | "Your safety score and recent events" |
| My Profile | "Your contact details and licence" |
Notifications: header bell.

## 3–5. Screens and actions
- **Today**: Vehicle (current assignment), Shift, Trips today, current/next trip; **Upcoming trips** (next 14 days). Trip actions with confirmation:
  | Button | Meaning |
  |---|---|
  | Accept | "Tells dispatch you will take this trip." |
  | Start trip | "Marks the trip as started now." |
  | Complete trip | "Marks the trip as completed now." |
  | Decline | "Tells dispatch you can't take this trip." (reason optional, ≤500) |
  | Request swap | "Asks dispatch to give this trip to another driver." |
  Buttons are disabled when they no longer apply (trip completed, cancelled, declined, already started or already responded).
- **My Shifts**: Current shift (**Start shift** / **End shift**, optional Odometer (km)), Working hours, Recent shifts (last 7 days).
- **My Leave**: **Request leave** (type CASUAL/SICK/ANNUAL/UNPAID/OTHER, first/last day, reason), Requests by status, **Cancel request**.
- **Shift Checklist**: template items → **Start checklist** → mark each item **Pass**/**Fail** ("What's wrong? (optional)"), Note → submit; Recent submissions (last 7 days).
- **My Safety**: Safety score (last 30 days), Events by type, Recent safety events.
- **My Profile**: Contact (Phone, Email, Address, Emergency contact/phone) → **Edit contact details**; Licence (Number, Class, Issued, Expires, Status); Employment (Hired on, IC card); **Change password**.

## 9. Workflows
**How do I use the driver application?** Sign in as **Tenant user** with your tenant code and driver login → you land in **My Work**. Each day: start your shift (My Shifts → Start shift), submit the pre-trip checklist, accept and start your dispatched trip, complete it, end your shift.
**What is my current shift?** My Shifts → Current shift.
**Show my assigned vehicle**: My Work → Today → Vehicle.
**What is my checklist status?** Shift Checklist → Recent submissions.
**What is my leave request status?** My Leave → Requests by status.
**Show my safety score**: My Safety.

## 10–11. Roles / permissions
Only driver logins (role DRIVER, `platform=false`) holding `driver.app` + `own.data.read`. Administrators holding the same codes are **not** given My Work. The account must be **linked to a driver profile** (else 403 "Your account is not linked to a driver profile").

## 16. Business rules
- A driver only ever sees their own data; the server identifies the driver from the login.
- Drivers cannot open fleet screens (Fleet Overview, Live Monitoring, Drivers, etc.); the server refuses driver logins on fleet data (verified 2026-10-31).

## 18. Common questions
- **Why can't a driver access the admin dashboard?** Drivers only hold `driver.app` and `own.data.read`; the dashboard needs `device.read`, and the server rejects driver tokens on fleet APIs.
- **Why do I get "not linked to a driver profile"?** Your login isn't linked to a driver record; ask your fleet manager to set *Linked user id* on your driver record.

## 19. Limitations
Driver writes untested live; driver preferences not available; the current Iris assistant needs `device.read`, so drivers don't get it yet.
