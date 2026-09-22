# Internal adversarial review — 22 September 2026

**Subsequent verification:** [CI run 35691832262](https://github.com/shi1720/DAISI/actions/runs/35691832262), revision `1ba692e`, completed successfully. Backend/frontend checks and all four functional browser journeys passed, including accessibility of the expanded cleaning comparison. The actual walkthrough was captured separately at `21c1f1f`; its recording test passed, while its broader run found three low-contrast banner nodes. The later revision corrects those colors. Exact capture and verification boundaries are preserved in `output/video/provenance.json`. A source ZIP exported at `c279088` was independently extracted, installed with frozen dependencies, built and started locally; a fresh guest created the expected 225-meal proposal, preserved all five sources and exported a valid PDF. Video assembly also passed H.264-only and H.264/AAC checks at 175 seconds using temporary test silence, with the execution-status footer visually inspected. These checks do not establish cloud deployment, field validation or video publication. The original heuristic scores remain unchanged.

This is an internal heuristic assessment, not an official score, prediction of placing, or independent external validation. The reviewer also contributed platform artifacts earlier in the project. The purpose of this pass is to challenge the current submission and expose defects. Implementation was not edited during the review; several findings were fixed by the implementation agents after the first report and are recorded below.

**Final integrity recheck:** the original code defects below have been repaired. Local API regressions verify preserved plan provenance across a snapshot refresh, suppression of mismatched or unversioned evaluations, and reset of reviewed status after edits. The workspace identity and bounded-body tests also pass. The final evidence addendum records the subsequently added calendar/error regressions and delivered artifact checks. Workspace sign-in and deployment are being handled separately; no cloud execution result is inferred from sign-in or from these local tests.

Scope: the current React application, API and owner-scoped stores, planning engine, ingestion snapshot, Databricks bundle/notebook/pipeline, deployment bootstrap, and the three-page `output/pdf/hawkerbridge-round1-v2.pdf`. The PDF was text-extracted and all three pages were rendered and inspected. The rubric weights come from the [official participant guide](https://daisi.online/guide); eligibility and submission details are separately tracked in `docs/rules-and-eligibility.md`.

## Original verdict and scores

These scores are retained from the initial artifact review, before the repair recheck. They have not been re-scored or treated as an official evaluation. Read the repair statuses below for the current implementation evidence.

**Round 1: credible, distinctive shortlist candidate; 84/100 on this internal scale.** The strongest idea is the workflow from a known closure to a constrained, reviewable response. The weak point is evidence that a coordinator needs this enough to adopt and pay for it. A strong-looking application does not answer that question.

| Round 1 criterion | Score | Reason |
| --- | ---: | --- |
| Problem fit and social impact | 25/30 | The user and decision are recognisable. The dated closure example is concrete. The proposed impact is a testable target, but no buyer workflow observation or beneficiary validation has occurred. |
| Solution quality and originality | 26/30 | Comparing changeable closure dates before spending on mitigation is stronger than another closure map. Budget, capacity, provenance, private plans and coordinator review form a coherent product. The optimisation itself is not a defensible moat. |
| Data and technical feasibility | 21/25 | Named official data, functioning local integration, quarantined bad intervals, governed publication design and restrained platform cost make the build credible. Intended deployment remains unproven, and the evidence-versioning fixes below matter. |
| Clarity of submission | 12/15 | Three slides follow the requested structure and can be read without narration. The product is still mostly explained through paragraphs; one concrete decision example would make the difference easier to remember. |
| **Total** | **84/100** | **Concept assessment; not a claim of eligibility or acceptance.** |

**Round 2 at the initial review: 65/100, provisional and not submission-ready.** No verified workspace execution or judge-accessible Databricks demonstration was available in that review. That is a gating weakness for a Databricks challenge regardless of a numerical score. The code earns feasibility credit; actual cloud evidence must be assessed separately.

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

| Finding | Current disposition | Verification boundary |
| --- | --- | --- |
| Engine version in cloud evaluation | Closed in code | Pipeline/store regressions plus API current/stale/unversioned tests pass; cloud publication still needs an actual run. |
| Workspace authentication deployment guard | Closed in code | Runtime guard, missing identity, CSRF, forged local headers, forbidden local registration and owner-isolation tests pass against a mocked durable store; genuine platform proxy behaviour remains a deployment check. |
| Calendar bounds and failed-update display | Closed in code and targeted DOM tests | Manifest-derived bounds, fallback date, loading-only spinner and explicit stale notice exist. Both dedicated regressions now pass; see the final evidence addendum. |
| SQL food-centre density | Closed in code | Real query reconciles 120 food centres / 123 inventory records locally and excludes a synthetic zero-food market. |
| Request-body limit | Closed in code | Declared-length rejection before read, streamed overflow early stop and accepted chunked replay tests pass. |
| Saved-plan provenance | Closed in code | Restart with new inputs leaves the saved record, JSON, result fingerprint and brief bound to the original sources. |
| Reviewed status after title/note edits | Closed in code | Both edits persist draft status and remove reviewer metadata; explicit re-review remains available. |

### P1 — Preserve the engine version in cloud evaluation and reject unversioned reports

**Repair status:** addressed in the owned platform files after review. The pipeline now hashes imported `engine.py` before snapshot fingerprinting and persists it in the manifest, every scenario and MLflow artifacts/parameters. `load_evaluation` rejects missing, malformed or mixed engine hashes and embedded input mismatches, and returns the validated engine hash. Regression tests cover each rejection, the successful publication, and engine changes during publication. The API's running-code comparison remains the final check before calling a report current.

The root agent also changed the API comparison to require a matching code hash, including reports where the field is absent.

**Recheck:** `test_evaluation_is_current_only_for_matching_inputs_and_engine` now verifies a valid report is returned, while changed data, changed engine and absent engine hash all produce `evaluation_status="stale"` with the report withheld. Store-level tests separately verify missing/mixed cloud scenario hashes.

**Original evidence:** `databricks/pipeline.py:evaluate` writes the input fingerprint and a constant model version into scenario results; `DatabricksStore.load_evaluation` returns no engine-code hash. `backend/hawkerbridge/api.py:evidence` checks `engine_code_sha256` only when it is present.

**Original failure:** rerun or deploy a changed `engine.py` against an existing published snapshot without rerunning the pipeline. The app calculates plans using the changed engine but accepts the old cloud evaluation as `current`, because the data fingerprint still matches and an absent code hash does not count as stale. The local evaluation already has stronger version checking than the cloud report.

**Recommended repair:** hash the actual imported engine source during pipeline evaluation; record it in the published manifest, every scenario result and the MLflow artifact/parameters. Return one validated, consistent hash from `load_evaluation`. Require a matching hash in the API; missing historical hashes should produce an explicit unversioned/unavailable status. Do not change the published snapshot after computing its fingerprint.

**Regression:** load a cloud report for identical data but another engine hash and assert that `/api/evidence` withholds it. Also reject mixed scenario hashes and an absent hash. Then test the valid matching report.

### P1 — Prove the Databricks authentication boundary and fail closed outside the supported runtime

**Repair status:** closed at the code/test level. `Settings.validate` requires the managed Apps runtime variables before enabling workspace-header authentication. `tests/test_workspace_auth.py` verifies that absent runtime markers fail startup, local mode ignores forged workspace identities, missing workspace identity returns 401, local registration is disabled, CSRF binds to the authenticated identity, and a second identity cannot read the first identity's plans. Runtime variables are a misconfiguration guard, not cryptographic proof; actual proxy-only reachability remains a deployment check.

**Original evidence:** `backend/hawkerbridge/api.py:platform_user` trusts `X-Forwarded-User` and `X-Forwarded-Email`. Those are the correct [Databricks Apps headers](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/http-headers), but the trust boundary is the platform proxy. `Settings.validate` currently checks storage mode and warehouse presence, with no guard against starting this mode on a standalone server. The implementation contract says this mode is enabled only inside that runtime. Existing API tests exercise local identity; SDK store mocks do not prove this boundary.

**Original failure:** a deployment operator runs the app on an ordinary reachable server with Databricks storage and auth enabled. A caller can supply the forwarded identity headers, receive that identity's CSRF token and access its owner-scoped records. This is a misdeployment risk, **not a demonstrated bypass of the genuine Databricks proxy**.

**Recommended repair:** add a clear startup guard for the expected Databricks Apps runtime and document the proxy-only contract. Such a marker prevents accidental configuration; it does not cryptographically authenticate headers. Preserve the network boundary that makes the headers trustworthy. Add lifecycle tests for missing headers, valid platform identity, CSRF, forbidden local register/login routes and cross-owner plans with a mocked durable store. Confirm real proxy behaviour in the deployment checklist.

### P2 — Bound the calendar by the published closure schedule and distinguish failure from loading

**Repair status:** closed in code and targeted DOM tests. The date field now derives its bounds from the manifest, ignores invalid date edits and selects the schedule's first day when today falls outside the available year. A spinner is displayed only while loading; failed requests explicitly label the last successful result as potentially stale and prevent generation. The final evidence addendum records both dedicated failure/year-boundary regressions passing. This reviewer did not change frontend files.

**Original evidence:** `frontend/src/App.tsx` initialises to today's date, permits `2020-01-01` through `2040-12-31`, and renders the `Updating access outlook…` pill whenever the displayed analysis date differs from the selected date. The backend correctly rejects a year outside `snapshot.manifest.closures_year`.

**Original failure:** select a 2027 date against the delivered 2026 schedule. The API returns a clear error, but the old analysis remains under a perpetual updating indication even after the request is finished. Starting the application after the schedule year also begins with an unsupported default.

**Recommended repair:** derive input bounds and an explicit archived-schedule fallback date from the manifest, while retaining the server check. Show loading only while a request is active; a failed analysis should be labelled stale or withheld. Include every analysis parameter in the freshness comparison, including planning area and rescheduled closures.

**Regression:** select a date outside the supported year, simulate request failure and start with a clock outside the schedule year. Assert there is no permanent spinner and no old result presented as the current selection.

### P2 — Make the SQL dashboard's cooked-food coverage definition agree with the engine

**Repair status:** addressed after review. Query 7 now exposes distinct `inventory_centres` and `food_centres` and uses only positive food-stall records in cooked-food density. A regression executes the actual query against the archived snapshot (123 inventory / 120 food centres) and adds a zero-food synthetic market to verify it cannot improve coverage. This local SQLite execution checks the portable calculation; it is not a claim of Databricks warehouse execution.

**Original evidence:** `databricks/sql/dashboard_queries.sql`, query 7, counts every row in `published_centres`. The engine now deliberately excludes the three official records with zero food stalls from cooked-food access; the source has 123 listed centres but 120 with food stalls.

**Original failure:** the BI density calculation calls all 123 records hawker coverage while the application calculates accessibility using 120. An evaluator comparing the governed SQL output with the app can reasonably challenge the conflicting supply definition.

**Recommended repair:** count `food_stalls > 0` for the cooked-food coverage measure. If total centre inventory is useful, expose it separately with a distinct label. Name the density denominator and snapshot year clearly.

**Regression:** an all-Singapore aggregate should reconcile to 120 food centres and separately to 123 inventory records; a synthetic zero-food market must never increase cooked-food coverage.

### P2 — Enforce the request-size cap before buffering the entire request

**Repair status:** closed at the code/test level. The outer ASGI `BodyLimitMiddleware` rejects an oversized declared length without reading the body, checks accumulated streamed bytes before buffering further chunks, and replays accepted bodies to the app. `tests/test_body_limit.py` verifies declared-length rejection, stopping before the unread remainder of an oversized stream and accepted chunked requests. This replaces the previous unbounded `request.body()` check.

**Original evidence:** API security middleware uses `len(await request.body()) > 65536`. That establishes a schema-size policy but reads the entire body into memory first.

**Original failure:** an oversized or chunked POST can allocate far more than 64 KB before returning 413. The endpoint need not pass authentication to reach this middleware. This is a resource-exhaustion hardening gap, not evidence of data disclosure.

**Recommended repair:** reject an oversized declared content length early and also bound the streamed bytes so chunked or dishonest clients cannot bypass the cap. Preserve downstream request handling for accepted bodies. Verify both declared-length and streamed-overflow requests return 413 without invoking the route or buffering the remainder.

## Findings already repaired after the initial review report

| Finding and reproduction | Current evidence | Remaining verification |
| --- | --- | --- |
| Advanced settings used setup-cost `min=1`, `step=50`, default `300`; native form validity was false because 300 is not 1 + 50n. Opening the panel blocked a default Generate action. | The field now uses `step=0.01`; `frontend/src/App.integration.test.tsx` asserts the expanded form is valid before generation. | Run the live API integration test and a browser pass with the panel open. |
| Title and note controls allowed more characters than the API accepted (160 vs 140; 10,000 vs 4,000). | Create/edit forms now use 140/4,000, with integration assertions. | Keep limits aligned with the request schema when changing them later. |
| Plans lacked an immutable source manifest; `/api/brief` returned the current snapshot's sources for a historical saved plan. JSON exports therefore did not contain the promised full provenance. | New plans store `source_manifest` and `engine_code_sha256`; briefs use preserved sources and explicitly mark legacy plans without a manifest. `test_saved_provenance_survives_restart_with_new_published_inputs` saves under A, restarts with B and confirms the persisted record, JSON and brief remain bound to A. | The local regression passes. Confirm the same durable lifecycle after an actual cloud publication/restart. |
| A title or note edit could leave a plan presented as already reviewed. | The API now resets such edits to draft and removes `reviewed_at`/`reviewed_by`. `test_editing_reviewed_plan_requires_fresh_review` checks title and note edits through the response, stored GET and JSON export, plus explicit re-review. | Regression passes; review status still represents a proposal review, never service dispatch. |

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

Final backend recheck: `uv run pytest -q tests/test_api.py tests/test_workspace_auth.py tests/test_body_limit.py` — **24 passed**. This includes seven newly added provenance, evaluation-freshness and review-lifecycle cases. Test fixtures use isolated local storage and clearly synthetic evaluation/source metadata; no committed source archive is altered. No new backend implementation defect requiring a change was found in this bounded pass.

## Final evidence addendum — 22 September 2026

This addendum refreshes the evidence record only. The original **84/100 Round 1** and **65/100 provisional Round 2** internal scores are unchanged. Completed local/browser checks, supplied submission files and actual Databricks execution are separate forms of evidence.

### Regression closure

`frontend/src/App.safety.test.tsx` now covers the two previously outstanding calendar/error cases. A simulated browser date of 20 January 2027 initialises analysis to the available 2026 schedule, sets input bounds to that year, and never sends the unsupported date. A simulated failed refresh shows the prior-result warning, removes the updating message and disables proposal generation. The focused command `npm test -- --run src/App.safety.test.tsx` was run during this pass: **2 tests passed**. These are DOM regression tests with a mocked map and network, not geographic rendering tests.

The completed real Chromium journey also opens advanced settings and checks native form validity with the default S$300 setup cost. It generates and saves a real proposal through the running local API, exercises the review checklist and downloads an actual PDF. That closes the earlier browser-validation follow-up for the invalid input step. The action remains a test proposal; no operational venue review or service dispatch is implied.

### Submission artifacts inspected

| File | Verified in this pass | Scope |
| --- | --- | --- |
| `output/pdf/hawkerbridge-round1.pdf` | **3 pages**, readable extracted text covering problem, solution/data and intended architecture/impact | Canonical Round 1 template-format deck. |
| `output/pdf/hawkerbridge-concept-note.pdf` | **1 page** | Supplemental concept note; it does not replace the canonical three-page template artifact. |
| `output/pdf/hawkerbridge-final-pitch.pdf` | **9 pages** | Within the ten-slide final-round limit; actual local screenshots, source/method limits, baseline results, unvalidated buyer pricing and prospective pilot targets are present. |
| `output/pdf/hawkerbridge-video-narration.pdf` | **3 pages** | Verbatim narration and screen timings; wording explicitly describes verified local execution. Human narration and uploaded video remain separate completion steps. |

The final pitch's architecture slide explicitly says **“Workspace execution pending”** and **“Local execution verified.”** Its pilot slide states that the targets remain unachieved. This pass checked page counts, text and screenshot provenance; final rendered-slide and video QA is being handled separately. It does not retroactively claim a visual review of a new PDF version based on the earlier v2 review.

At inspection, the canonical Round 1 PDF SHA-256 was `8cddcb28ca7865eecacdc01ca4b7c9996a8690284a7fa06586bd3806c6daeccc`; the nine-page final pitch SHA-256 was `f6c03fd93c911924669456e758d8a3bab9e9ab1107b7709195846750b63b0e7b`. These identify the files inspected, not every later rebuild.

### CI and screenshot provenance

[Run 35689097551](https://github.com/shi1720/DAISI/actions/runs/35689097551) completed successfully on source commit `94b96cf7994093bc77a23eac1171c9a2624a784e`. It passed four real Chromium journeys covering the authenticated planning workflow, account sign-in, scope/counterfactual/zero-budget behaviour and mobile layout. The optional walkthrough recording was skipped in that run. All eight image hashes in `docs/screenshots/provenance.json` were checked against the actual supplied PNGs. Both deck screenshot crops and their original CI captures also match `scripts/presentations/assets/screenshots.json`.

[Run 35690578006](https://github.com/shi1720/DAISI/actions/runs/35690578006) targets commit `507c3545fdd6bd78e44e70ecbcf685157bf538ff`. At the 05:29 UTC status check, backend tests, frontend tests/build/audit and browser installation had passed; the browser/recording step was still running, with compression and artifact preservation pending. No completion or delivered-video claim is made from that partial status. The screenshots already supplied retain their earlier successful-run provenance rather than being relabelled as images from this newer run.

### Remaining gates

Actual source-to-plan execution in Databricks, the workspace identity boundary and viewer permissions, the published AI/BI dashboard, and final video upload still require their own direct evidence. The Lakeview definition and bundle configuration are supplied and offline-validated, but neither a file nor a successful local CI run proves a cloud deployment. `submission/team.json` still leaves institution, course, year and email unresolved and does not certify Singapore IHL eligibility. No stakeholder interview, customer payment or field outcome has been added to the evidence record.
