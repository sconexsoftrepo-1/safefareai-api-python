---
module: Leave Management
feature_keys:
- leave
- leave-requests
- approve-leave
- reject-leave
- request-leave
- pending-leave
- leave-types
routes:
- /drive-vision/workforce?tab=leave
- /drive-vision/my-work/leave
roles:
- fleet users with workforce.*; drivers via My Work
permissions:
- workforce.read
- workforce.create
- workforce.update
- own.data.read (driver)
availability: Read VERIFIED; writes NOT VERIFIED
technical_reference: api/modules/leave_management_api.md
---

# Leave Management

## 1. Purpose
Drivers request leave; fleet managers see, create (on behalf of a driver), approve or reject leave requests. Approved leave affects availability and dispatch conflict checks.

## 2. Navigation
- Fleet: **Workforce → Leave** tab.
- Driver: **My Work → My Leave**.

## 3. Screens
Fleet: Leave requests table (driver, Type, Dates, status), **Request leave for a driver**, Approve/Reject dialog with "Note (optional)" and the dispatches affected by the leave. Driver: Requests by status, **Request leave**, **Cancel request**.

## 6. Form
Driver (fleet form only, required: "Choose a driver"), **Leave type** (CASUAL, SICK, ANNUAL, UNPAID, OTHER), **First day**, **Last day** (not before first day), **Reason** (≤ 500).

## 9. Workflows
**How can I approve a leave request?**
1. Fleet → **Workforce** → **Leave** tab.
2. Find the pending request.
3. **Approve** or **Reject** → optional note → confirm. The dialog lists dispatches affected by the leave; what happens to them is decided by the server.
**Request leave for a driver**: Leave tab → **Request leave for a driver** → driver, type, dates, reason → submit.
**Driver: request leave**: My Work → My Leave → **Request leave** → type, first/last day, reason → submit. Cancel a pending one with **Cancel request**.

## 11. Permissions
List `workforce.read`; create `workforce.create`; approve/reject `workforce.update`; driver self-service `own.data.read` (+ `driver.app`).

## 18. Common questions
- **Which drivers have pending leave requests?** Workforce → Leave (status PENDING); Fleet Overview shows the "Pending leave" count.
- **What is my leave request status?** (driver) My Work → My Leave.
- **What leave statuses are there?** Leave request status values: PENDING, APPROVED, REJECTED, CANCELLED.

## 19. Limitations
Writes not verified live.
