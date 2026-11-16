---
module: Reports
feature_keys:
- reports
- mileage-report
- driving-report
- parking-report
- media-report
- export
routes:
- /drive-vision/reports
roles:
- users with report.read
permissions:
- report.read; report.schedule (schedules — no screen)
availability: VERIFIED LIVE; no download
technical_reference: api/modules/reports_api.md
---

# Reports

## 1. Purpose
Tabular reports per device and period: **Mileage**, **Driving**, **Parking** and **Media** (captured images/videos).

## 2. Navigation
Sidebar **Monitor → Reports**.

## 3. Screen
- **Report** selector: Mileage · Driving · Parking · Media.
- **Time range**: Today · Last 7 days (default) · Last 30 days, and device filter (**All devices** or one device).
- **Load again up to the current time** (refresh).

## 7. Columns
| Report | Columns |
|---|---|
| Mileage | Device, Period, Distance (sortable), Odometer start, Odometer end; total km summed from rows |
| Driving / Parking | Device, Start, End, Duration |
| Media | Device, Captured, Channel, Type · trigger (raw codes), File (**Open**) |

## 8. Paging
Driving, Parking and Media: server paging, 20 per page. Mileage: not paged.

## 9. Workflows
**How can I generate a report?** Reports → pick the **Report** type → choose the time range → (optional) pick a device → results load automatically. Use **Load again up to the current time** to refresh.
**How can I download reports?** There is **no download/export button** in the current app. The backend can export and schedule reports (CSV/XLSX/PDF), but no screen offers it yet — NOT IMPLEMENTED IN FRONTEND.

## 10–11. Roles / permissions
`report.read`.

## 16. Business rules
Media links rendered only for real http(s) URLs. Media type and trigger are shown as raw codes (meanings undocumented).

## 17. Errors
503 shown as "unavailable", not empty. "Couldn't load the device list for the filter."

## 18. Common questions
- **How do I see total distance driven?** Reports → Mileage → range → the total km is summed from the rows.
- **Can I schedule reports by email?** Not from the app (the backend supports it, but there is no screen).

## 19. Limitations
No export/download, no idle report tab, no schedules screen.
