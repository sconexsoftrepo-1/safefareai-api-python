---
module: Dispatch
feature_keys:
- dispatch
- dispatched-trips
- new-dispatch
- conflict-check
- cancel-dispatch
- swap-request
- approve-swap
- verification
routes:
- /drive-vision/dispatch
- /drive-vision/dispatch?tab=swaps
roles:
- users with dispatch.read
permissions:
- dispatch.read
- dispatch.create
- dispatch.update
availability: Read VERIFIED (empty); writes NOT VERIFIED
technical_reference: api/modules/dispatch_api.md
---

# Dispatch

## 1. Purpose
Plan work for drivers: a **dispatch** assigns a driver and vehicle to a scheduled job (title, times, origin → destination, instructions). The server checks conflicts (driver on leave, overlapping dispatch, …), drivers accept/decline/start/complete it in My Work, and swap requests let a trip move to another driver.

## 2. Navigation
Sidebar **Fleet → Dispatch**. Subtitle "Dispatched trips, conflict checks and driver swaps".

## 3. Screens (**View**)
- **Dispatches** — Window: Next 14 days · Past 14 days · All. Columns: Dispatch (title), Scheduled, Driver, Vehicle, Status, Swap pending.
- **Conflicts** — server-detected scheduling conflicts.
- **Swap requests** — From → to, Reason, Decision (Pending), **Approve** / **Reject** with Note (optional).
- Dispatch detail: Status, Driver, Vehicle, Route, Reporting time, Instructions, Route notes, Responded · started · completed, Declined, Cancelled, verification checks (Passed / Failed); buttons **Edit**, **Cancel dispatch**, **Request swap**.

## 6. New / Edit dispatch form
| Field | Required | Rule |
|---|---|---|
| Title | yes | ≤ 150 |
| Driver | yes | picker (first 100 active drivers) |
| Vehicle | yes | picker |
| Scheduled start / Scheduled end | yes | end after start; IST |
| Reporting time | no | valid time |
| Origin / Destination | no | ≤ 300 |
| Instructions / Route notes | no | ≤ 1000 |
Status values: ASSIGNED, ACCEPTED, DECLINED, IN_PROGRESS, COMPLETED, CANCELLED.

## 9. Workflows
**Create a dispatch**
1. Dispatch → **New dispatch**.
2. Fill Title, Driver, Vehicle, Scheduled start/end (IST) and optional fields.
3. **Check conflicts** (this only checks; it creates nothing). Result: "No conflicts found" or "The server reported conflicts".
4. Save becomes enabled only after the current draft was checked → confirm "Create this dispatch?" ("The dispatch is saved on the server and the driver may be notified").
**Approve a swap request**: Dispatch → View **Swap requests** → **Approve** or **Reject** (optional note).
**Cancel**: open dispatch → **Cancel dispatch** (optional reason).

## 10–11. Roles / permissions
`dispatch.read` (screen); `dispatch.create`; `dispatch.update` (edit, cancel, request swap, approve/reject swaps).

## 16. Business rules
Allowed status transitions are decided by the server (undocumented); statuses shown as returned. Dispatches can be cancelled but not deleted.

## 17. Errors
"The server rejected the request/decision" toasts; 409 for invalid transitions.

## 18. Common questions
- **What is dispatch?** Assigning a planned trip to a driver and vehicle.
- **Why was my dispatch rejected?** The server found a conflict (driver on leave/busy, vehicle busy) or the transition isn't allowed.

## 19. Limitations
Writes not verified live; whether creating a dispatch sends SMS/push to the driver is NOT VERIFIED.
