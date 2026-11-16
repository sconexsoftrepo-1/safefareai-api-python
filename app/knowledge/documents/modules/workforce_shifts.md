---
module: Workforce — availability, shifts and checklists
feature_keys:
- workforce
- shifts
- availability
- on-shift
- working-hours
- checklists
- pre-trip-checklist
- checklist-template
routes:
- /drive-vision/workforce
- /drive-vision/workforce?tab=leave
roles:
- users with workforce.read
permissions:
- workforce.read
- workforce.create
- workforce.update
availability: VERIFIED LIVE (read)
technical_reference: api/modules/workforce_shifts_api.md
---

# Workforce — availability, shifts and checklists

## 1. Purpose
Shows which drivers are available, on shift, on a trip or on leave for a day; recent shifts; leave requests (see `leave_management.md`); submitted pre-trip checklists and the checklist template.

## 2. Navigation
Sidebar **Fleet → Workforce**. Subtitle "Driver availability, shifts, leave and pre-trip checklists".

## 3. Tabs (**View**)
1. **Availability** — Day (IST); KPIs Leave pending, On shift, Scheduled h, Upcoming; per-driver status (AVAILABLE, ASSIGNED, ON_SHIFT, ON_TRIP, ON_LEAVE — shown raw), Phone.
2. **Shifts** — "Shifts · last 7 days", filter Driver (All drivers); columns Started, Open/Ended, Duration, Distance.
3. **Leave** — see `leave_management.md`.
4. **Checklists** — "Submitted checklists · last 7 days" (Submitted, Result: All passed / Failed items) and **Checklist template** ("Items drivers are asked to check").

## 9. Workflows
**Who is on shift now?** Workforce → Availability (today) → On shift; or Shifts tab → open shifts.
**What is my current shift?** (driver) My Work → **My Shifts**.

## 11. Permissions
`workforce.read`.

## 18. Common questions
- **What is a shift?** A driver's working period, started and ended by the driver in My Work (start can record odometer).
- **What is the pre-trip checklist?** The vehicle checks a driver submits (Pass/Fail per item) before driving; template from the server.
- **What availability statuses exist?** Driver availability status values: AVAILABLE, ASSIGNED, ON_SHIFT, ON_TRIP, ON_LEAVE (shown as returned by the server).

## 19. Limitations
Fleet users can't edit the checklist template in the app.
