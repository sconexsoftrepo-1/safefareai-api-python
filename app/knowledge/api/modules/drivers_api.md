---
module: Drivers
user_document: documents/modules/drivers.md
roles:
- users with driver.read
permissions:
- driver.read
- driver.create
- driver.update
- driver.delete
- alarm.read (safety panel)
- device.read (vehicle picker)
apis:
- GET /api/v1/drivers
- GET /api/v1/drivers/{id}
- POST /api/v1/drivers
- PUT /api/v1/drivers/{id}
- DELETE /api/v1/drivers/{id}
- GET /api/v1/drivers/licence-expiries
- GET /api/v1/drivers/{id}/assignments
- GET /api/v1/drivers/{id}/safety-score
- GET /api/v1/drivers/{id}/safety-events
sources:
- src/app/drive-vision/drivers/page.tsx
- src/components/drive-vision/drivers/drivers-page.tsx
- src/components/drive-vision/drivers/drivers-model.ts
- src/features/drive-vision/api/operations-service.ts
- src/features/drive-vision/api/insight-service.ts
status: Reads VERIFIED LIVE 2026-10-29; writes IMPLEMENTED, NOT VERIFIED
---

# Drivers — API and implementation reference

Technical companion of `documents/modules/drivers.md`. For the Iris tool layer and developers; not for quoting to end users.

## 13–15. API
`DriverDto {id, userId, name, status ACTIVE|INACTIVE, phone, email, gender, address, dateOfBirth, emergencyContactName, emergencyContactPhone, hiredOn, icCardNo, remark, licence {…status VALID|EXPIRING|EXPIRED|MISSING}, currentAssignment, createdAt, updatedAt}`. `GET /drivers?keyword&status&pageNumber&pageSize`; `GET /drivers/licence-expiries?withinDays`.

## Technical details referenced by the user document

- Sidebar **Fleet → Drivers** (`/drive-vision/drivers`).
| New driver | driver.create (+tenant) | `POST /drivers` |
| Edit | driver.update | `PUT /drivers/{id}` |
| Delete | driver.delete | `DELETE /drivers/{id}` |
- `userId` is only shown as "Linked user"; it is never treated as the signed-in identity. Safety data comes only from the server.
- Server field errors shown per field; unknown driver → 404 (but `/safety-events` returns 200 empty — backend inconsistency #35).
