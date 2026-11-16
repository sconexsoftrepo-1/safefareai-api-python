# SafeFare Iris AI — API and implementation knowledge (technical)

For the Iris **tool layer**, intent → API mapping, and developers. **Not for quoting to end users.** The user-facing knowledge is in `../documents/`.

```
api/
  README.md
  api_reference.md              GENERATED: all 242 Swagger operations — permission, params, body/response schema, used by frontend?
  permission_api_map.md         GENERATED: permission code → operations that need it
  architecture.md               system parts, frontend layout, env vars, conventions
  backend_gaps.md               missing APIs, open backend questions (#ids, GA-ids), frontend/backend inconsistencies
  api_test_cases.json           test questions answered from this folder
  modules/<module>_api.md       per module: endpoints, params, payloads, responses, source files, verification status, technical notes
```

Each `modules/<module>_api.md` has front matter `module`, `user_document`, `apis`, `sources`, `status` (with verification dates and evidence), and the API sections moved out of the user document.

## Swagger conventions (summary)
Envelope `{code,msg,data,total,extend}`; vendor reads carry `extend.source` (VENDOR/LOCAL), `stale`, `fallbackReason` (`VENDOR_EMPTY`); errors carry `extend.errorCode`, `fieldErrors`, `requestId`; paging `pageNumber` from 1, `pageSize` 1–100; times ISO-8601 UTC, ranges `[from,to)`; Safe-Fare Admin writes need `tenantId`/`X-Tenant-Id` (400 `TENANT_REQUIRED`); `/api/v1/driver/**` returns only the caller's driver data. Details in `api_reference.md`.
