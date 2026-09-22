# Final rubric and release review

Updated 22 September 2026 for source `b539db724c3731897595e81061a73070655920cf`. This is an internal assessment, not an official judge score, a winning prediction or a security certification. Weights follow the [official final-solution rubric](https://daisi.online/guide). The scale is ten points per criterion, multiplied by its published weight.

**Internal score: 84/100.** The actual narrated hosted video and both rebuilt decks exist and have recorded verification. Final hosted acceptance has now passed all four application journeys, following a test-only correction to an overly short initial-readiness timeout. Adoption, measured benefit and eligibility remain separate unresolved questions.

| Official criterion | Weight | Assessment | Weighted score | Evidence and remaining limit |
| --- | ---: | ---: | ---: | --- |
| Social impact | 30% | 7/10 | 21/30 | Named coordinator workflow, credible continuity decision and measurable pilot protocol. No observed uptake, operator interview, paid commitment or welfare outcome is verified. |
| Technical execution on Databricks | 30% | 9/10 | 27/30 | Successful governed pipeline, twelve quality checks, nine MLflow scenarios, four query datasets, published AI/BI dashboard, native App OAuth checks and actual Delta isolation/concurrency tests. Native workspace browser rendering and a second real workspace identity remain unverified. |
| Solution and user experience | 20% | 9/10 | 18/20 | Complete analysis, cleaning comparison, private-plan and export workflow. Four final hosted browser journeys, HTTP, isolation, stale-edit rejection and rollout persistence passed. Automated accessibility checks found no serious or critical violations on the tested screens. Operator usability and venue capacity remain unvalidated. |
| Data rigour | 10% | 9/10 | 9/10 | Five official sources, original bytes/hashes/dates, quarantine, preserved proposal evidence and mathematical feasibility checks. Dated census, representative points, omitted food alternatives and unsupported waste/permanent-closure labels are disclosed. |
| Presentation | 10% | 9/10 | 9/10 | Concrete 225/450/450 story, reviewed three-slide and nine-slide decks, public 175-second narrated hosted recording and 33 timed captions. Presenter rehearsal and a clear response to the data limitations still matter. |

## Numbers and claims checked

Recomputed the released engine against the promoted Databricks snapshot. On **28 September 2026**, at **800 metres**, there are **17 scheduled centre closures**, **1,025 listed food stalls** inside those centres, and **six flagged subzones** containing **91,180 Census 2020 residents**, including **17,120 seniors**. These are area-screen totals; they are not people observed to need food. Inventory contains 123 records, of which 120 have food stalls.

At 5% assumed participation, S$4 per meal, S$300 setup, 150 meals per locality, at most three localities and senior weight 2: **S$1,500 → 225 planned meals / S$1,500 spending / two localities; S$3,000 → 450 / S$2,700 / three; S$6,000 → 450 / S$2,700 / three**. No meals or venues are booked. The ceiling follows the declared capacity and site limit; it is an operational question to verify, not a discovered real-world service capacity.

Two evaluations use the same promoted source fingerprint `a3b84df2577a59a9d1cf6ccaf8cb45b47a0caffa4429122e1f409a29de274c4f` and engine SHA-256 `9833154988fb5f35063982802db4884694ec2e3a5971f641cde3088942abfdcd`, but **different scenario sets**:

| Evidence | Actual execution and scenarios | Supported objective uplift claim |
| --- | --- | --- |
| [Local robustness evaluation](../data/processed/evaluation.json) | 15 unique local runs on the cloud-published snapshot. Dates Sep 22, Sep 28 and Dec 14; primary budgets S$1,500/3,000/6,000 at 800 m; additional 500/1,200 m reach checks. All 15 pass the feasibility audit. | **0.3%–9.2% across nine primary cases**. The full 15-case range is 0.3%–13.8%; do not attach the primary range to a different set. |
| [Databricks evaluation](../data/processed/databricks-evaluation.json) | Nine actual cloud runs: **Sep 22, Oct 5 and Dec 14 × S$600/1,500/3,000**, all at 800 m. | **2.8%–9.2% across the nine cloud cases**. These are policy-weighted model objectives, not observed welfare or predictive accuracy. |

The **Sep 28 presentation is an API recomputation from the cloud publication**, not one of the nine recorded cloud evaluation cases. The [execution record](../data/processed/databricks-publication.json) records pipeline `SUCCESS`, parent MLflow `FINISHED`, twelve passing checks and four query datasets. Three tabular sources were fetched live; two URA geometry archives were reused with their original timestamps and verified checksums. “Five sources freshly downloaded in Databricks” would be inaccurate. The API now withholds stale, missing, failed or mismatched cloud proof.

## Commercial assessment

The [business case](business-case.md) is appropriately cautious. Its S$1,000 pilot, S$250–500 monthly subscription, support-hour assumptions and hosting allowances are explicitly experiments, not sales, quotations or forecasts. All three contribution calculations reconcile, including the negative downside case. Founder time is costed, meal-operation costs are separated from software revenue, and Databricks Free Edition is correctly excluded as the basis for a paid production promise.

The critical assumption is task frequency. A single site's occasional cleaning closure may not create enough work for a subscription; a multi-site operator or scoped project fee is more plausible. At S$300/month and S$30/hour, ten saved hours merely offset the subscription before onboarding and verification. Require a named accountable buyer, measured baseline preparation time and repeat willingness to pay before presenting commercial traction. Public data and an optimiser are not a moat. Do not delay a useful pilot to add a speculative LLM feature: no paid LLM is required by the current product.

## Final evidence and verification boundaries

| Evidence | Verified result | Boundary |
| --- | --- | --- |
| [Local CI 35696909209](https://github.com/shi1720/DAISI/actions/runs/35696909209) | Completed successfully on `b539db7`, including backend, frontend and browser workflow checks. | Local-runner success does not establish public hosting acceptance. |
| [Final hosted acceptance 35697740614](https://github.com/shi1720/DAISI/actions/runs/35697740614) | Completed successfully against `hawkerbridge-api-00006-lnl`: 180 backend tests, 30 frontend tests and four hosted browser journeys passed. Tested source `16b538d` changes initial readiness to a bounded twenty-second API-success wait, without retries; deployed product code is `b539db7`. | One opt-in frontend integration test and the optional recording test were intentionally skipped. The four application journeys all ran. A passing check is not an accessibility certification or availability SLA. |
| [Hosted HTTP acceptance](../output/hosted-smoke.json) | Managed sign-in, two-user isolation, 225/450/450, all exports, CSRF/origin boundaries, current evidence and stale-edit rejection passed. | HTTP verification is distinct from visual/accessibility/browser acceptance. |
| [Rollout persistence](../output/hosted-restart-smoke.json) | A named account and saved proposal survived a container rollout; disposable test data was deleted. | This establishes the recorded rollout, not an availability SLA. |
| [Native Databricks verification](databricks-verification.json) | Final App deployment uses source `b539db7`; deployed backend/frontend file hashes match. OAuth health, platform session, nine-case evidence and all three budget scenarios passed. The actual Delta concurrency/isolation test passed. | Native browser/map/mobile rendering, a second real workspace user and dashboard visual rendering are explicitly unverified. |
| [Retention verification](firebase-retention-verification.json) | Hourly scheduler enabled; authenticated scheduled invocation, execute and dry runs succeeded; saved deletion command survived dry-run. | Guest expiry and bounded cleanup are operational controls, not a commercial service guarantee. |
| [Public narrated video](https://youtu.be/vioVop-MEVA) and [provenance](../output/video/narrated-provenance.json) | Studio confirmed public publication; the watch page played the 175-second video with the correct title, author and English captions. Unauthenticated oEmbed returned 200. The local H.264/AAC file checksum reconciles; 1600 × 900, 33 captions and fourteen documented visual sample points. Synthetic Cedar narration is disclosed. | The video is a recorded demonstration using the earlier capture revision below. Playback verification does not establish universal network or device compatibility. |

The hosted video preserves its actual capture provenance: recording test passed on earlier source `6cd7e8` in run `35695869659`; another journey in that run found a Leaflet teardown defect, subsequently fixed. The recording is not relabelled as a capture of `b539db7`. [Capture provenance](../output/demo-footage/provenance.json) identifies this boundary. Final hosted run `35697740614` separately verifies the corrected product. The preceding run's five-second readiness assertion was resolved by waiting for the initial API success, not by retrying a failed application journey.

The public application uses the verified `a3b84df…` data publication. The repo is public, with `main` as its only branch. The official three-slide Round 1 and nine-slide final decks were rebuilt and visually reviewed with current cloud and hosted evidence. The narrated MP4 and public video are delivered artifacts. After Shivam's explicit final authorisation, Devpost project `1192740` displayed “Project submitted!” with the updated story, testing evidence, five captioned screenshots, public video and official Round 1 PDF. Academic details remain incomplete; submission does not establish eligibility. Gallery captures come from run `35697233597` on product `b539db7`; successful run `35697740614` verifies that unchanged product.

## Closed release findings

The earlier retention dry-run bug is fixed: preview executes with temporary arguments and preserves the scheduled `--execute` command. The earlier HTML caching bug is fixed: actual HTML/SPA response revalidation passed. Revision checks prevent stale edits or resurrection of deleted plans. Firebase Hosting uses the forwarded `__session` cookie, managed Firestore replaces ephemeral public SQLite, and origin/CSRF/owner checks passed hosted HTTP tests.

Read-only deployment checks confirmed public Firestore access returns 403 and unauthenticated private API routes return 401 with no-store headers. The API itself is intentionally publicly invokable, with application authentication protecting private data. A dedicated managed identity runs the API, and the scheduler may invoke its specific retention job. A narrow code/configuration pattern scan found no private key, GitHub token or Databricks PAT; this is not a comprehensive secret-scanner guarantee.

Earlier stale roadmap/API-contract statements were corrected. Publication copy distinguishes the nine cloud cases from the fifteen local cases and three live tabular downloads from two reused geometry archives. Historical local screenshots and recordings retain their original capture labels.

## Remaining decisions

1. The source/submission archive builder passed manifest verification with 183 source files and 67 delivery files. Release archives are regenerated from the final metadata commit; use their manifests to identify the precise revision.
2. Computer Science is the participant-supplied course. Confirm Singapore IHL eligibility, institution, year and team particulars with Shivam before an eligibility attestation. The Devpost primary contact was taken from the verified signed-in account; student eligibility cannot be inferred from that account or the implementation.
3. Rehearse the three-minute presentation and explain the proxy, capacity assumptions, two evaluation sets and data limitations without equating scenario meals with deliveries or residents with measured need.
4. Validate one real operator workflow before claiming adoption or impact. The proposed 30% preparation-time reduction, S$1,000 pilot and S$250–500 monthly subscription remain hypotheses. A rare single-site closure may justify a project fee rather than recurring software spend.

The strongest story remains a coordinator deciding what to verify before funding support. Technical completeness does not supply customer evidence, prove eligibility or guarantee a prize.
