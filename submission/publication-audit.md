# Publication handoff and rubric audit

Internal notes, updated 22 September 2026, for Devpost project **1192740**. The narrated video is public and verified. After Shivam explicitly authorised accepting the final terms and submitting, Devpost displayed **“Project submitted!”** and listed DAISI under **Submitted to**. Academic details remain incomplete; platform submission is not proof of eligibility.

## Field map

| Field | Content |
| --- | --- |
| Name | HawkerBridge |
| Tagline | Turn hawker closure notices into practical, reviewable community support plans. |
| Problem | C3: KopilamAI |
| Story | `submission/devpost-description.md` |
| Testing | `submission/testing-instructions.md` |
| Built with | Python, TypeScript, React, FastAPI, SciPy, HiGHS, Shapely, Databricks, Delta Lake, Unity Catalog, MLflow, Lakeflow, Leaflet, Firebase Hosting, Firebase Authentication, Cloud Firestore, Cloud Run. |
| Code | https://github.com/shi1720/DAISI |
| Website | https://hawkerbridge-sg.web.app |
| Video | [Public narrated demonstration](https://youtu.be/vioVop-MEVA), 175 seconds, with 33 English captions. Studio publication, watch-page playback and unauthenticated oEmbed resolution are verified. |
| Round 1 | `output/pdf/hawkerbridge-round1.pdf`, official three-slide format |
| Final deck | `output/pdf/hawkerbridge-final-pitch.pdf`, nine pages |
| Team | Shivam Gupta. Primary contact is taken from the verified signed-in account. Computer Science is the supplied course. Institution, year and eligibility still require verified participant information. |

Preserve the existing Devpost project. Fill any additional form-specific fields from actual evidence. Do not attest to unknown student status.

## Verified execution and release acceptance

The Databricks pipeline completed successfully: publication `69cbf18aae9c4f1883b629ab0de25843`, finished parent MLflow run, twelve passing quality checks, nine scenario results and four executed dashboard SQL datasets. Three tabular sources were fetched live; two URA geometry archives were reused with their original timestamps and checked hashes. The public [execution record](../data/processed/databricks-publication.json) contains the run evidence. A verified CLI login alone would not establish this, but actual execution has now been read back and checked.

The public Firebase site passed hosted HTTP acceptance on revision `hawkerbridge-api-00002-6x7`, including managed sign-in, two-user isolation, 225/450/450 allocations, all exports, evidence fingerprints, CSRF/origin rejection and stale-edit 409. A named account and saved proposal then survived rollout to `hawkerbridge-api-00003-92d`; the disposable account was deleted. See `output/hosted-smoke.json` and `output/hosted-restart-smoke.json`. The active fingerprint matches `a3b84df2577a59a9d1cf6ccaf8cb45b47a0caffa4429122e1f409a29de274c4f`.

[Final hosted run 35697740614](https://github.com/shi1720/DAISI/actions/runs/35697740614) completed successfully against revision `hawkerbridge-api-00006-lnl`: 180 backend tests, 30 frontend tests and all four application browser journeys passed. The opt-in frontend integration test and optional recording test were intentionally skipped. Tested source `16b538d` changes the initial API-success wait to twenty seconds without retries; product code remains `b539db7`, which also passed complete [local CI 35696909209](https://github.com/shi1720/DAISI/actions/runs/35696909209). This resolves the preceding run's overly short readiness assertion. The narrated hosted video has checksum/media/caption verification plus fourteen sampled visual checks. YouTube Studio confirmed public publication; the watch page played the 175-second video with the correct title and author, English manual captions were visible, and unauthenticated oEmbed returned 200 for the public link.

Public authentication uses verified Firebase `__session` cookies, exact origins and CSRF, not Databricks forwarding headers. Owner-scoped Firestore replaces ephemeral SQLite. Stale edits return 409 and deleted plans cannot be recreated by an in-flight patch. The enabled hourly retention schedule successfully invoked its worker; execute and dry runs passed, with the saved deletion command preserved. The deployed HTML/SPA revalidation headers also passed acceptance. These results close the retention and caching findings. See `docs/firebase-retention-verification.json`.

## Keep the two evaluations separate

| Evidence | Actual scenario set | Supported claim |
| --- | --- | --- |
| Local robustness | 15 unique cases on the promoted snapshot; Sep 22/Sep 28/Dec 14, budgets S$1,500/3,000/6,000, plus reach sensitivity | All feasible. Nine primary cases show 0.3%–9.2% policy-weighted objective uplift. |
| Databricks MLflow | Sep 22/Oct 5/Dec 14 × S$600/1,500/3,000, all at 800 m | Nine real cloud comparisons; 2.8%–9.2% policy-weighted objective uplift. |

The Sep 28 demonstration is an API recomputation from published data, not one of the nine cloud evaluation cases. Its verified numbers are 17 scheduled closures, six flagged subzones and 91,180 historical area residents; S$1,500/S$3,000/S$6,000 produce 225/450/450 planned meals at S$1,500/S$2,700/S$2,700 spending. These are neither beneficiaries nor delivered meals.

## Criteria, adoption and attribution

The [official guide](https://daisi.online/guide) assigns final weights of 30% social impact, 30% Databricks execution, 20% UX, 10% data rigour and 10% presentation. The [final internal review](../docs/final-rubric-review.md) scores current evidence at 84/100; that is not an official judge score or winning prediction. C3 covers hawker access and closure evidence. HawkerBridge deliberately narrows the problem to temporary continuity, without fabricating permanent-closure trends or centre-level waste labels.

The guide specifies the common three-slide Round 1 template and 6 October 2026, 11:59 PM SGT deadline. Current Singapore IHL eligibility remains unverified. AI assistance is permitted, and Shivam is accurately credited as project owner who initiated the brief and set product goals; no personal coding history or stakeholder interviews are invented.

Lead with the coordinator's cleaning comparison and the S$3,000 versus S$6,000 capacity plateau. The buyer, schedule owner, meal operator and resident may differ. Pricing and the 30% preparation-time target remain pilot hypotheses, with no customers, partnerships or revenue claimed. Cloud Run requires linked billing and Databricks Free Edition is noncommercial; do not promise cost-free commercial hosting.

## Release packaging and participant follow-up

1. The archive builder completed with 183 committed source files and 67 delivery files, validating every SHA256 manifest entry and the 35 MB size limit. Release archives are regenerated from the final metadata commit; their manifests identify that exact revision. Preserve accurate capture history: the video was recorded from an earlier hosted revision, not relabelled as the latest source.
2. Complete missing member details only from verified participant information. The updated official Round 1 PDF, including Computer Science, was attached before submission. Workspace URLs may require authorised access, and credentials must never be shared.

The user authorised filling the existing project and public YouTube publication. This authorisation does not justify claiming unfinished checks, unknown eligibility or an upload that has not happened.

Current publishing handoff: [Devpost submission](https://devpost.com/software/hawkerbridge) is submitted and remains editable before the deadline. It includes the final story, testing evidence, five captioned screenshots, public video and updated official Round 1 PDF. Primary contact was taken from the verified signed-in account. Gallery screenshots were captured by run `35697233597` on product `b539db7`; later successful run `35697740614` verifies the unchanged application. Computer Science is confirmed as the course. Institution, year and current Singapore IHL eligibility remain unverified. No missing academic facts were invented.
