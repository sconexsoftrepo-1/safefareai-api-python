# Knowledge test results

Executed 2026-11-05 with `tools/run_knowledge_tests.py`, separately for each knowledge set.

- **Grounding**: the expected document contains every key term of the answer.
- **Retrieval top-3**: plain BM25 keyword search over `##` chunks *within that set only* ranks the expected document in the top 3.
- **Answerable in top-3**: some top-3 document contains all key terms.
- Not tested here: the Iris LLM, live API answers, authorisation (Phase 5/8).

## documents/ (user-facing)

Cases 258 · grounding 258/258 · retrieval top-3 241/258 (top-1 203) · answerable top-3 254/258

| Module | Cases | Grounding | Retrieval top-3 | Answerable top-3 |
|---|---|---|---|---|
| Dashboard | 10 | 10/10 | 9/10 | 10/10 |
| Live Monitoring | 10 | 10/10 | 10/10 | 10/10 |
| Historical Video | 9 | 9/9 | 9/9 | 9/9 |
| Trips | 9 | 9/9 | 8/9 | 9/9 |
| Reports | 10 | 10/10 | 10/10 | 10/10 |
| Vehicles | 10 | 10/10 | 10/10 | 10/10 |
| Devices | 10 | 10/10 | 10/10 | 10/10 |
| Sensors | 10 | 10/10 | 10/10 | 10/10 |
| Drivers | 10 | 10/10 | 9/10 | 9/10 |
| Driver Assignments | 9 | 9/9 | 8/9 | 9/9 |
| Dispatch | 10 | 10/10 | 10/10 | 10/10 |
| Workforce/Leave | 10 | 10/10 | 9/10 | 10/10 |
| Workforce/Shifts | 10 | 10/10 | 10/10 | 10/10 |
| Alerts | 10 | 10/10 | 9/10 | 9/10 |
| AI alarms | 9 | 9/9 | 9/9 | 9/9 |
| Routine alarms | 8 | 8/8 | 8/8 | 8/8 |
| Safety | 10 | 10/10 | 10/10 | 10/10 |
| Safety scores | 9 | 9/9 | 9/9 | 9/9 |
| Geofences | 9 | 9/9 | 9/9 | 9/9 |
| Users | 10 | 10/10 | 8/10 | 8/10 |
| Tenants | 10 | 10/10 | 9/10 | 10/10 |
| Roles | 10 | 10/10 | 6/10 | 10/10 |
| Settings | 10 | 10/10 | 10/10 | 10/10 |
| Driver app | 12 | 12/12 | 9/12 | 12/12 |
| Auth | 9 | 9/9 | 9/9 | 9/9 |
| General | 3 | 3/3 | 3/3 | 3/3 |
| Troubleshooting | 3 | 3/3 | 2/3 | 3/3 |
| Notifications | 3 | 3/3 | 3/3 | 3/3 |
| Search | 1 | 1/1 | 1/1 | 1/1 |
| Maintenance | 2 | 2/2 | 2/2 | 2/2 |
| Commands | 2 | 2/2 | 2/2 | 2/2 |
| Iris | 1 | 1/1 | 1/1 | 1/1 |

Not in top 3:

- KT-009 — What is the Expiring tile? (expected modules/dashboard_overview.md, rank 4, answerable PASS)
- KT-040 — What permission is needed for trips? (expected modules/trips_tracking.md, rank 4, answerable PASS)
- KT-088 — What fields are required for a driver? (expected modules/drivers.md, rank 6, answerable FAIL)
- KT-098 — What permission is needed to assign? (expected modules/driver_assignments.md, rank 4, answerable PASS)
- KT-121 — What is the max reason length? (expected modules/leave_management.md, rank 4, answerable PASS)
- KT-134 — What is the difference between an alarm and an alert? (expected modules/alerts_incidents.md, rank 5, answerable FAIL)
- KT-196 — Can I delete a user? (expected modules/users_sub_accounts.md, rank 4, answerable FAIL)
- KT-201 — Can I edit roles on the Users screen? (expected modules/users_sub_accounts.md, rank 12, answerable FAIL)
- KT-211 — How do I go back to all tenants? (expected modules/tenants_organizations.md, rank 4, answerable PASS)
- KT-214 — What roles exist in SafeFare? (expected roles_permissions.md, rank 21, answerable PASS)
- KT-215 — What permission opens Live Monitoring? (expected roles_permissions.md, rank 28, answerable PASS)
- KT-217 — Can a tenant admin see other tenants? (expected roles_permissions.md, rank 4, answerable PASS)
- KT-221 — Which permission opens Device Commands? (expected roles_permissions.md, rank 7, answerable PASS)
- KT-234 — Show my assigned vehicle (expected modules/driver_my_work.md, rank 5, answerable PASS)
- KT-237 — Show my safety score (expected modules/driver_my_work.md, rank 5, answerable PASS)
- KT-243 — Can drivers use Iris today? (expected modules/driver_my_work.md, rank 4, answerable PASS)
- KT-258 — Why is the dashboard not loading? (expected troubleshooting.md, rank 15, answerable PASS)

## api/ (technical)

Cases 32 · grounding 32/32 · retrieval top-3 28/32 (top-1 20) · answerable top-3 31/32

| Module | Cases | Grounding | Retrieval top-3 | Answerable top-3 |
|---|---|---|---|---|
| Dashboard | 2 | 2/2 | 2/2 | 2/2 |
| Historical Video | 1 | 1/1 | 1/1 | 1/1 |
| Driver Assignments | 1 | 1/1 | 1/1 | 1/1 |
| AI alarms | 1 | 1/1 | 1/1 | 1/1 |
| Routine alarms | 2 | 2/2 | 2/2 | 2/2 |
| Safety scores | 1 | 1/1 | 1/1 | 1/1 |
| Geofences | 1 | 1/1 | 1/1 | 1/1 |
| Auth | 2 | 2/2 | 1/2 | 2/2 |
| Vehicles | 2 | 2/2 | 2/2 | 2/2 |
| Devices | 1 | 1/1 | 1/1 | 1/1 |
| Drivers | 2 | 2/2 | 1/2 | 1/2 |
| Trips | 2 | 2/2 | 2/2 | 2/2 |
| Alerts | 1 | 1/1 | 1/1 | 1/1 |
| Leave | 1 | 1/1 | 1/1 | 1/1 |
| Workforce | 1 | 1/1 | 1/1 | 1/1 |
| Dispatch | 1 | 1/1 | 1/1 | 1/1 |
| Safety | 1 | 1/1 | 1/1 | 1/1 |
| Notifications | 1 | 1/1 | 1/1 | 1/1 |
| Driver app | 2 | 2/2 | 1/2 | 2/2 |
| Tenants | 1 | 1/1 | 0/1 | 1/1 |
| Sensors | 1 | 1/1 | 1/1 | 1/1 |
| Permissions | 1 | 1/1 | 1/1 | 1/1 |
| Conventions | 2 | 2/2 | 2/2 | 2/2 |
| Gaps | 1 | 1/1 | 1/1 | 1/1 |

Not in top 3:

- API-014 — Which API lists drivers? (expected modules/drivers_api.md, rank 6, answerable FAIL)
- API-024 — Which API returns the driver's assigned vehicle? (expected modules/driver_my_work_api.md, rank 7, answerable PASS)
- API-025 — Which API lists tenants for the Safe-Fare Admin? (expected modules/tenants_organizations_api.md, rank 4, answerable PASS)
- API-027 — Which API returns my permissions? (expected modules/authentication_login_api.md, rank 6, answerable PASS)
