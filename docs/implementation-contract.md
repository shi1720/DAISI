# HawkerBridge implementation contract

Current interface contract for the September 2026 release. The executable request schemas are in `backend/hawkerbridge/schemas.py`; `/api/openapi.json` describes their exact constraints. Response structures below summarise the fields used by the product. A scenario is a planning proposal requiring venue and operator verification, not dispatched assistance.

## Runtime and identity

| Mode | Identity | Persistence | Boundary |
| --- | --- | --- | --- |
| Public Firebase | Firebase email/password or anonymous guest, verified by the Admin SDK | Cloud Firestore | Exact HTTPS origins, secure `__session` cookie, CSRF and verified owner ID |
| Local | Local accounts or isolated guests | SQLite | Loopback evaluation environment, opaque `hb_session` cookie and CSRF |
| Databricks | Managed workspace identity | Governed Delta plan table through SQL warehouse | Trusted Databricks Apps proxy only; never enable its identity headers behind another public proxy |

The snapshot is immutable for the life of an API process. Local and Firebase modes load the bundled snapshot; Databricks mode reads the published warehouse snapshot and fails closed if unavailable. Restart or roll out the application to adopt a newly verified publication. Firebase never falls back to local authentication or ephemeral plan storage.

All application endpoints use `/api` on the same origin. Fetch with credentials and send `X-CSRF-Token` for authenticated mutations. Hosted mutations also require an exact configured `Origin`, including login and account creation before a session exists. Errors use JSON `detail`; it is a string for application errors and may be a validation-error array for rejected schemas. Public health is `GET /api/health`; private data endpoints require identity.

## Authentication

`GET /api/auth/session` and successful sign-in responses return:

```json
{
  "user": {"id": "opaque-owner-id", "name": "Display name", "email": "", "mode": "guest"},
  "csrf_token": "session-bound-token",
  "auth_mode": "firebase"
}
```

`user` and `csrf_token` are null when signed out. `auth_mode` is `local`, `firebase` or `databricks`; user mode may additionally be `guest`. Request bodies never choose an owner.

- `POST /api/auth/demo {}` creates an isolated guest in local or Firebase mode.
- `POST /api/auth/register {name,email,password}` creates a local or Firebase account. Registration password length is 12–256 characters.
- `POST /api/auth/login {email,password}` signs into that runtime's account store.
- `POST /api/auth/reset-password {email}` is Firebase-only and returns a generic `message` without confirming account existence.
- `POST /api/auth/logout` revokes the session. Firebase guest logout also removes its workspace.
- `DELETE /api/auth/account` removes the authenticated local or Firebase account and its plans; workspace identities remain managed by Databricks.

Firebase uses an HttpOnly, Secure, SameSite=Lax `__session` cookie because Hosting forwards only that cookie. The CSRF token is bound to the verified cookie and works across API instances. Firebase normal logout revokes that session without deleting saved plans. Guests expire after seven days; hourly cleanup removes abandoned records and resumes partial account deletion. Signing into a named account does not migrate guest plans. No passwords or administrator credentials are seeded in the browser.

## Data and analysis

`GET /api/snapshot` returns `manifest`, `centres`, `closures`, `demand_zones`, planning-area population, boundaries, food-waste context and quarantined intervals. Source provenance includes dates, hashes, retrieval/reuse details, Census year and closure-calendar year.

- Centres include ID, name, coordinates, address, planning area and food/market stall counts. Zero-food-stall facilities remain in inventory but are excluded as food-access alternatives.
- Closures include ID, centre ID, start/end dates, `cleaning` or `works`, and original source text. Unknown or ambiguous dates are quarantined.
- Demand zones contain subzone ID, planning area, representative coordinates, Census residents/seniors and display geometry. They are aggregate observations, not identified beneficiaries.

`POST /api/analyse` accepts date, radius, senior weight, optional planning-area scope and hypothetical `rescheduled_closure_ids`. Only eligible cleaning events can be removed from that day's comparison. Analysis returns summary totals, centre status, zone baseline/current access, area rankings, calendar, limitations, model version and source fingerprint. Scoped demand still considers food alternatives across planning-area boundaries. Missing distances use null.

`POST /api/optimise` adds budget, setup cost, meal cost, site capacity, maximum sites and participation rate. It returns analysis, assumptions, proposed sites and allocations, totals, baseline, uptake sensitivity, deterministic explanation, model version, source fingerprint and limitations. Budget and costs are SGD per day. Results include `summary.total_meals`, `spent`, `sites_selected`, `estimated_demand`, `weighted_benefit`, `improvement_pct` and `solver_status`.

Meal demand is an explicit participation assumption applied to flagged census areas, not observed need. Candidate sites are geographic localities, not verified available venues. An optimisation decision covers one day; it does not book, purchase, deliver or change official dates.

## Private plans and revision conflicts

| Endpoint | Contract |
| --- | --- |
| `GET /api/plans` | Owner's lightweight plan metadata and summary; no full geometry payload per row |
| `POST /api/plans` | `{title,parameters,notes}`; computes the result server-side and assigns an ID |
| `GET /api/plans/{id}` | Owner's complete proposal, parameters, result and preserved source evidence |
| `PATCH /api/plans/{id}` | **Required** `expected_updated_at` from the loaded plan; optional title, notes and draft/reviewed status |
| `DELETE /api/plans/{id}` | Owner-only deletion; 204 on success |
| `GET /api/plans/{id}/export?format=pdf\|csv\|json` | Owner-only download |
| `GET /api/brief?plan_id={id}` | Deterministic sourced explanation from the saved result; no LLM required |

A stale edit returns 409 and tells the client to reopen the latest version. A missing/deleted plan returns 404. Updates check the revision atomically and never insert a deleted plan. The client keeps unsaved text for comparison, not silent overwrite. Editing title/notes resets reviewed status unless the request explicitly supplies status. Saved calculations and provenance remain unchanged.

All stores provide `get_plan`, `list_plans`, `save_plan`, `update_plan(owner,plan,expected_updated_at)` and `delete_plan`. Firestore creation quotas and revision updates use transactions; SQLite uses a conditional transaction; Databricks uses a parameterised owner-and-revision conditional UPDATE. Databricks table access is service-principal scoped, with application owner filtering, not database-enforced per-user row security.

## Evidence API

`GET /api/evidence` returns manifest, quarantine, national waste context, methodology and:

- `evaluation`, `evaluation_status`: the current benchmark or null with `current`, `stale` or `unavailable` status.
- `evaluation_execution`: `local` for the bundled 15-scenario robustness benchmark in local/Firebase mode; `databricks` for the SQL-backed nine-case report in native workspace mode.
- `workspace_execution`: verified publication record or null. It requires successful pipeline status, finished parent MLflow, matching publication/source/model hashes and passing recorded quality checks.
- `cloud_evaluation`: matching nine-case report or null, with unique scenario IDs and matching per-scenario source/model hashes.

The 15 local cases and nine cloud cases use different dates and budget grids; see `docs/evaluation.md`. Their objective scores are model comparisons, not predictive accuracy or observed impact. Missing, failed, malformed or stale execution artifacts are withheld. Source, model or publication changes require refreshed evidence before current verification is displayed.
