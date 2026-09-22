# Internal adversarial review — 22 September 2026

This is an internal heuristic assessment, not an official score, prediction of placing, or independent external validation. The reviewer also contributed platform artifacts earlier in the project. The purpose of this pass is to challenge the current submission and expose defects. Implementation was not edited during the review; several findings were fixed by the implementation agents after the first report and are recorded below.

Scope: the current React application, API and owner-scoped stores, planning engine, ingestion snapshot, Databricks bundle/notebook/pipeline, deployment bootstrap, and the three-page `output/pdf/hawkerbridge-round1-v2.pdf`. The PDF was text-extracted and all three pages were rendered and inspected. The rubric weights come from the [official participant guide](https://daisi.online/guide); eligibility and submission details are separately tracked in `docs/rules-and-eligibility.md`.

## Verdict and scores

**Round 1: credible, distinctive shortlist candidate; 84/100 on this internal scale.** The strongest idea is the workflow from a known closure to a constrained, reviewable response. The weak point is evidence that a coordinator needs this enough to adopt and pay for it. A strong-looking application does not answer that question.

| Round 1 criterion | Score | Reason |
| --- | ---: | --- |
| Problem fit and social impact | 25/30 | The user and decision are recognisable. The dated closure example is concrete. The proposed impact is a testable target, but no buyer workflow observation or beneficiary validation has occurred. |
| Solution quality and originality | 26/30 | Comparing changeable closure dates before spending on mitigation is stronger than another closure map. Budget, capacity, provenance, private plans and coordinator review form a coherent product. The optimisation itself is not a defensible moat. |
| Data and technical feasibility | 21/25 | Named official data, functioning local integration, quarantined bad intervals, governed publication design and restrained platform cost make the build credible. Intended deployment remains unproven, and the evidence-versioning fixes below matter. |
| Clarity of submission | 12/15 | Three slides follow the requested structure and can be read without narration. The product is still mostly explained through paragraphs; one concrete decision example would make the difference easier to remember. |
| **Total** | **84/100** | **Concept assessment; not a claim of eligibility or acceptance.** |

**Round 2 today: 65/100, provisional and not submission-ready.** There is no verified workspace execution or judge-accessible Databricks demonstration. That is a gating weakness for a Databricks challenge regardless of a numerical score. The code earns feasibility credit, not credit for a cloud run that has not happened.

| Round 2 criterion | Score | Reason |
| --- | ---: | --- |
| Social impact and realistic adoption | 19/30 | A plausible operator problem and explicit pilot measures; no observed planning-time saving, site verification, purchase signal or beneficiary outcome. |
| Technical execution on Databricks | 14/30 | A substantial real pipeline, Delta/Unity Catalog design, MLflow comparison and durable store exist. Static schema validation and SDK mocks do not establish serverless installation, permissions, successful publication or Apps operation in the target workspace. |
| Solution and user experience | 17/20 | Attractive, coherent authenticated workflow, editable assumptions, geographic scope, private save/review/export and failure states. The calendar issue below remains; current maps represent screening, not venue readiness. |
| Data rigour | 8/10 | Sources and hashes, quarantine, baseline comparisons, monetary feasibility and uncertainty are unusually explicit. Cloud model-version evidence and BI consistency still need repair. |
| Presentation | 7/10 | The concept deck is legible and disciplined. A rehearsed, timed video and a verified live cloud path have not been assessed in this pass. |
| **Total** | **65/100** | **Snapshot of evidence available now, not a forecast of the completed submission.** |

No points were deducted merely for using optimisation rather than an LLM. A natural-language model would not solve the main adoption uncertainty and is not required for this decision-support task.

## Prioritised findings and repair status

The initial findings below preserve their reproduction and rationale. Subsequent platform repairs are explicitly recorded under the relevant item; the original score is a review snapshot and has not been silently inflated after repairs.

### P1 — Preserve the engine version in cloud evaluation and reject unversioned reports

**Repair status:** addressed in the owned platform files after review. The pipeline now hashes imported `engine.py` before snapshot fingerprinting and persists it in the manifest, every scenario and MLflow artifacts/parameters. `load_evaluation` rejects missing, malformed or mixed engine hashes and embedded input mismatches, and returns the validated engine hash. Regression tests cover each rejection, the successful publication, and engine changes during publication. The API's running-code comparison remains the final check before calling a report current.

The root agent also changed the API comparison to require a matching code hash, including reports where the field is absent.

**Evidence:** `databricks/pipeline.py:evaluate` writes the input fingerprint and a constant model version into scenario results; `DatabricksStore.load_evaluation` returns no engine-code hash. `backend/hawkerbridge/api.py:evidence` checks `engine_code_sha256` only when it is present.

**Failure:** rerun or deploy a changed `engine.py` against an existing published snapshot without rerunning the pipeline. The app calculates plans using the changed engine but accepts the old cloud evaluation as `current`, because the data fingerprint still matches and an absent code hash does not count as stale. The local evaluation already has stronger version checking than the cloud report.

**Fix:** hash the actual imported engine source during pipeline evaluation; record it in the published manifest, every scenario result and the MLflow artifact/parameters. Return one validated, consistent hash from `load_evaluation`. Require a matching hash in the API; missing historical hashes should produce an explicit unversioned/unavailable status. Do not change the published snapshot after computing its fingerprint.

**Regression:** load a cloud report for identical data but another engine hash and assert that `/api/evidence` withholds it. Also reject mixed scenario hashes and an absent hash. Then test the valid matching report.

### P1 — Prove the Databricks authentication boundary and fail closed outside the supported runtime

**Evidence:** `backend/hawkerbridge/api.py:platform_user` trusts `X-Forwarded-User` and `X-Forwarded-Email`. Those are the correct [Databricks Apps headers](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/http-headers), but the trust boundary is the platform proxy. `Settings.validate` currently checks storage mode and warehouse presence, with no guard against starting this mode on a standalone server. The implementation contract says this mode is enabled only inside that runtime. Existing API tests exercise local identity; SDK store mocks do not prove this boundary.

**Failure:** a deployment operator runs the app on an ordinary reachable server with Databricks storage and auth enabled. A caller can supply the forwarded identity headers, receive that identity's CSRF token and access its owner-scoped records. This is a misdeployment risk, **not a demonstrated bypass of the genuine Databricks proxy**.

**Fix:** add a clear startup guard for the expected Databricks Apps runtime and document the proxy-only contract. Such a marker prevents accidental configuration; it does not cryptographically authenticate headers. Preserve the network boundary that makes the headers trustworthy. Add lifecycle tests for missing headers, valid platform identity, CSRF, forbidden local register/login routes and cross-owner plans with a mocked durable store. Confirm real proxy behaviour in the deployment checklist.

### P2 — Bound the calendar by the published closure schedule and distinguish failure from loading

**Evidence:** `frontend/src/App.tsx` initialises to today's date, permits `2020-01-01` through `2040-12-31`, and renders the `Updating access outlook…` pill whenever the displayed analysis date differs from the selected date. The backend correctly rejects a year outside `snapshot.manifest.closures_year`.

**Failure:** select a 2027 date against the delivered 2026 schedule. The API returns a clear error, but the old analysis remains under a perpetual updating indication even after the request is finished. Starting the application after the schedule year also begins with an unsupported default.

**Fix:** derive input bounds and an explicit archived-schedule fallback date from the manifest, while retaining the server check. Show loading only while a request is active; a failed analysis should be labelled stale or withheld. Include every analysis parameter in the freshness comparison, including planning area and rescheduled closures.

**Regression:** select a date outside the supported year, simulate request failure and start with a clock outside the schedule year. Assert there is no permanent spinner and no old result presented as the current selection.

### P2 — Make the SQL dashboard's cooked-food coverage definition agree with the engine

**Repair status:** addressed after review. Query 7 now exposes distinct `inventory_centres` and `food_centres` and uses only positive food-stall records in cooked-food density. A regression executes the actual query against the archived snapshot (123 inventory / 120 food centres) and adds a zero-food synthetic market to verify it cannot improve coverage. This local SQLite execution checks the portable calculation; it is not a claim of Databricks warehouse execution.

**Evidence:** `databricks/sql/dashboard_queries.sql`, query 7, counts every row in `published_centres`. The engine now deliberately excludes the three official records with zero food stalls from cooked-food access; the source has 123 listed centres but 120 with food stalls.

**Failure:** the BI density calculation calls all 123 records hawker coverage while the application calculates accessibility using 120. An evaluator comparing the governed SQL output with the app can reasonably challenge the conflicting supply definition.

**Fix:** count `food_stalls > 0` for the cooked-food coverage measure. If total centre inventory is useful, expose it separately with a distinct label. Name the density denominator and snapshot year clearly.

**Regression:** an all-Singapore aggregate should reconcile to 120 food centres and separately to 123 inventory records; a synthetic zero-food market must never increase cooked-food coverage.

### P2 — Enforce the request-size cap before buffering the entire request

**Evidence:** API security middleware uses `len(await request.body()) > 65536`. That establishes a schema-size policy but reads the entire body into memory first.

**Failure:** an oversized or chunked POST can allocate far more than 64 KB before returning 413. The endpoint need not pass authentication to reach this middleware. This is a resource-exhaustion hardening gap, not evidence of data disclosure.

**Fix:** reject an oversized declared content length early and also bound the streamed bytes so chunked or dishonest clients cannot bypass the cap. Preserve downstream request handling for accepted bodies. Verify both declared-length and streamed-overflow requests return 413 without invoking the route or buffering the remainder.

## Findings already repaired after the initial review report

| Finding and reproduction | Current evidence | Remaining verification |
| --- | --- | --- |
| Advanced settings used setup-cost `min=1`, `step=50`, default `300`; native form validity was false because 300 is not 1 + 50n. Opening the panel blocked a default Generate action. | The field now uses `step=0.01`; `frontend/src/App.integration.test.tsx` asserts the expanded form is valid before generation. | Run the live API integration test and a browser pass with the panel open. |
| Title and note controls allowed more characters than the API accepted (160 vs 140; 10,000 vs 4,000). | Create/edit forms now use 140/4,000, with integration assertions. | Keep limits aligned with the request schema when changing them later. |
| Plans lacked an immutable source manifest; `/api/brief` returned the current snapshot's sources for a historical saved plan. JSON exports therefore did not contain the promised full provenance. | New plans now store `source_manifest` and `engine_code_sha256`; briefs use preserved plan sources and explicitly mark legacy plans with no manifest. | A refresh/restart regression should save under snapshot A, run the app against B, and confirm the saved plan, JSON and brief still refer to A. |

## Deployment review outcome

No additional definite fresh-install blocker was established from static inspection. The bundle has one serverless task, pinned dependencies, an existing-warehouse resource, an app principal grant path, built frontend inclusion and explicit live/archive modes. Statements API handling polls pending requests and checks chunk completeness; SQL values are parameterised and owner predicates are present. These are substantive strengths.

What is still required is direct evidence: authenticate to the actual workspace, install the declared dependencies, create the app identity, run the job, inspect published tables and MLflow artifacts, restart the app, and verify two-user record isolation. Exercise the app with a user granted only app usage to prove it does not depend on the developer's table ownership. Keep SQL/app resource permissions least-privileged; do not solve deployment failures by granting end users direct access to other owners' plan rows. `docs/databricks-deployment.md` contains the execution checklist. A validated bundle file is not a deployment result.

## Submission improvements with the highest payoff

1. **Tell one decision story.** Use the 28 September example, then show the coordinator choosing between a cleaning-date change and support for an unavoidable closure. The real snapshot supports the deck's 17 scheduled closed centres and 1,025 food stalls. These are infrastructure counts, not an estimate of people missing a meal. Explain the next action and who approves it.
2. **Make the buyer hypothesis falsifiable.** Before claiming business viability, observe one coordinator perform their current planning task, record time and required inputs, then repeat it with HawkerBridge. Ask whether this happens frequently enough for recurring procurement. A paid-pilot/subscription price is still a proposed experiment. Do not convert plausible staff-time arithmetic into claimed ROI.
3. **Show the path from suggestion to a usable site.** Candidate localities still need venue permission, staffing, food-safety arrangements, accessibility checks and service capacity. Retain the existing review gate, and make the pilot scorecard show whether each proposal survives those checks. The product's value may be a faster verified shortlist even when the first allocation is rejected.
4. **Lead the cloud demo with evidence.** One successful job, one raw source record, one quarantined interval, one governed published table and one genuine baseline comparison will demonstrate more technical quality than a list of Databricks product names. Then show a budget change and export a private plan.
5. **Tighten the Round 1 slide 1 byline.** The v2 text places “Shivam Gupta” immediately beside “Problem statement”; add spacing or a separator. The rendered three-page layout is legible with no clipping. Keep the concise concept wording; use the larger final deck for richer screenshots and the verified decision example.

The highest-value next milestone is a verifiable source-to-plan Databricks run with corrected version evidence. After that, one real workflow observation is more valuable than adding a chatbot, a new speculative predictor or another visual panel.

## Verification recorded in this pass

- Before the platform repairs: `uv run pytest -q tests/test_api.py tests/test_databricks_store.py` — 34 passed.
- After platform repairs: `uv run pytest -q tests/test_databricks_store.py` — 29 passed, including real-engine publication evaluation and the cooked-food density regression.
- `uv run ruff check databricks backend/hawkerbridge/databricks_store.py tests/test_databricks_store.py` — passed.
- Round 1 v2: text extracted; all three pages rendered and visually inspected; the 28 September infrastructure counts were checked against the real engine output.
- No workspace deployment, production load test, external stakeholder interview or official judging occurred in this review.
