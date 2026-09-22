# Judge testing instructions

Open [HawkerBridge](https://hawkerbridge-sg.web.app) and select **Explore as a guest**. No API key, shared password or Databricks account is required for the public application. Named accounts use email/password through Firebase Authentication; private proposals use Cloud Firestore. Code and reproducible setup are at [github.com/shi1720/DAISI](https://github.com/shi1720/DAISI).

**Release status:** actual Databricks execution, hosted HTTP acceptance and saved-plan persistence across a container rollout passed. The public checks cover sign-in, owner isolation, 225/450/450 allocations, exports, source evidence, CSRF/origin boundaries and stale edits. Final hosted browser journeys and video review remain in progress. See `output/hosted-smoke.json`, `output/hosted-restart-smoke.json` and `submission/deployment-status.json` for the exact evidence boundary.

## Five-minute walkthrough

1. Choose **28 September 2026**, **All Singapore**, and **800 m access**. The released data shows 17 scheduled closed centres, 1,025 listed food stalls and six flagged subzones. Their Census 2020 totals are 91,180 residents, including 17,120 aged 65 or above. These are area-screen totals, not verified beneficiaries.
2. Inspect a closed-centre marker and its dates. “No resolved closure” is not confirmation that a facility is operating.
3. Open **Continuity planner** and **What if cleaning moved?** Select **Bedok Reservoir Road Blk 630**. The modelled area total changes to 54,030 under that hypothetical change. Select **Reset scenario** before the budget comparison. Renovation closures cannot be removed through this cleaning-only control; no official date is changed.
4. Use **S$1,500 budget**, **5% uptake**, **S$4 per meal**, **3 maximum localities**, **S$300 setup per locality**, **150 meals per locality** and **2x senior priority**. Generate a proposal. Expect **225 planned meals**, two proposed localities and **S$1,500 spend**.
5. Set **S$3,000**, regenerate, then set **S$6,000** and regenerate. Both produce **450 planned meals** and **S$2,700 spend**. Inspect the capacity and uptake-sensitivity explanations. Localities and capacities require operator verification.
6. Save a proposal with non-personal test notes. Inspect the review checklist and export PDF, CSV and JSON. Marking a test proposal reviewed does not verify a real venue or dispatch food.
7. Edit the title or notes. The proposal returns to draft and removes reviewer metadata while retaining its original result and sources. If another tab has changed the plan, a stale save is rejected; reopen the latest version and compare before retrying.
8. Open **Evidence & methods**. Inspect source years, quarantine, limitations and the separate local and Databricks evaluation sections. Confirm the active publication fingerprint matches the execution record. Delete test proposals when finished.

These exact numbers require the released 22 September snapshot and the stated assumptions. If data changes, update instructions, screenshots and video together.

## Privacy and failure checks

- A fresh private-browser guest cannot see another workspace's proposals, including by changing a plan URL.
- Zero budget produces a valid zero-allocation outcome; negative budget is rejected. Changed assumptions require regeneration.
- An analysis failure stops loading, labels the earlier result stale and prevents generation until recovery.
- Named-account persistence across a backend revision change and fresh login passed in the hosted restart test. This goes beyond a local page reload; repeat it when changing persistence or deployment configuration.
- Guest logout deletes its workspace. Abandoned guests expire after seven days and are purged by an hourly retention job. Signing into a named account does not migrate an earlier guest's plans.
- Account settings allow a named account and its private plans to be deleted. A partial deletion blocks access and is retried by cleanup.
- Do not enter beneficiary identities, phone numbers, health information or case histories. Use synthetic coordination notes. Do not send password-reset emails as part of an automated test.

## Verified Databricks evidence

[The recorded pipeline](https://dbc-6fea141d-04eb.cloud.databricks.com/?o=7474659582484876#job/929729986607018/run/1046237288082887) completed successfully. Its parent MLflow run finished, twelve quality checks passed, and all four dashboard SQL datasets executed. Workspace links require authorised Databricks access; the public [execution record](https://github.com/shi1720/DAISI/blob/main/data/processed/databricks-publication.json), repository and application expose the relevant evidence without sharing credentials.

Three tabular datasets were fetched live. Two URA geometry archives were reused with their original dates and checked hashes. All five retain provenance. Firebase hosting is the public serving layer; it does not replace the Databricks pipeline or imply that this website is a Databricks App.

| Evaluation | Scenario set | Interpretation |
| --- | --- | --- |
| Local robustness | 15 unique runs; Sep 22/Sep 28/Dec 14, budgets S$1,500/3,000/6,000, primary 800 m plus 500/1,200 m sensitivity | All feasible; nine primary cases improve the policy-weighted objective by 0.3%–9.2%. |
| Databricks MLflow | Nine runs; Sep 22/Oct 5/Dec 14 × S$600/1,500/3,000, all 800 m | Actual cloud objective improvement 2.8%–9.2%. |

The Sep 28 walkthrough recomputes from the published data; it is not one of the nine cloud evaluation cases. Neither evaluation measures hunger, delivered meals or welfare.

## Reproducible local fallback

```sh
uv sync --frozen --extra dev
npm --prefix frontend ci
npm --prefix frontend run build
uv run python scripts/start_app.py
```

Open `http://127.0.0.1:8000` and select **Explore as a guest**. Local mode uses a separate SQLite workspace, not the hosted Firebase account. It runs the same planner against the bundled verified snapshot. Describe a local fallback as local when presenting it.
