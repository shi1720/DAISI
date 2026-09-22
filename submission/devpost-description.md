# HawkerBridge

**A closure continuity desk for Singapore.** C3 — KopilamAI · Project owner: Shivam Gupta

## The problem

A familiar hawker centre closes for cleaning or repairs. Its regular customers can read the notice, but a community coordinator faces a different question: which neighbourhoods lose a nearby option, and what support is feasible with the people, venues and money available?

HawkerBridge connects the closure notice to that planning decision. It is designed for estate operators and community organisations coordinating temporary support. Residents do not need another app.

## What it does

Choose a date and a proximity threshold. HawkerBridge compares the listed hawker network before and during scheduled closures, highlights affected subzones and exposes the demographic assumptions behind the map. A coordinator can test a hypothetical cleaning change, enter a support budget and compare proposed collection localities against a simple largest-demand-first allocation.

The result is a saved, reviewable proposal with cost, capacity, assumptions, source fingerprints and PDF, CSV and JSON exports. Collection localities are candidates for verification, not booked venues. Saving a plan does not dispatch meals or alter a published closure date.

## A decision the demo makes concrete

On **28 September 2026**, our archived NEA data lists **17 scheduled centre closures**. At an **800-metre straight-line threshold**, six populated subzones lose coverage at their representative points. Those subzones contain **91,180 Census 2020 residents**, including **17,120 aged 65 or above**. This is an aggregate exposure screen; it does not mean 91,180 people are hungry, rely on hawker food or lack other food options.

Under explicitly editable assumptions—5% participation, S$300 setup per locality, S$4 per meal, 150 meals per locality and at most three localities—a S$1,500 daily budget supports **225 planned meals**. S$3,000 supports **450**. Raising the budget to S$6,000 still supports **450**, with S$2,700 allocated.

The useful insight is the binding capacity constraint: more money alone does not expand this scenario. A coordinator must verify additional capacity or consider a different service arrangement. These are planned allocations, not measured deliveries.

## Data and engineering

The build uses five Singapore national open datasets: [NEA hawker closures and centre inventory](https://data.gov.sg/datasets/d_bda4baa634dd1cc7a6c7cad5f19e2d68/view), [SingStat Census 2020 subzone age counts](https://data.gov.sg/datasets/d_d95ae740c0f8961a0b10435836660ce0/view), [URA planning-area boundaries](https://data.gov.sg/datasets/d_4765db0e87b9c86336792efe8a1f7a66/view), [URA subzone boundaries](https://data.gov.sg/datasets/d_8594ae9ff96d0c708bc2af633048edfb/view) and [national waste statistics](https://data.gov.sg/datasets/d_daf568968ab40dc81e7b08887a83c8fa/view). Waste figures provide national context only; they do not estimate hawker-centre waste.

The verified snapshot contains 123 centres, of which 120 have listed food stalls, and 332 census subzones. Ingestion preserves raw source bytes, checksums and provenance; normalises closure intervals; quarantines unknown or ambiguous dates; validates joins; and publishes a replacement snapshot only after checks pass. A failed refresh preserves the last good snapshot. Missing or unresolved closure information is never evidence that a centre is definitely open.

The Databricks deployment is implemented as a serverless Lakeflow Job: archived source responses in Bronze, typed and quality-checked Delta tables in Silver, and published access outputs in Gold under Unity Catalog. MLflow records scenario parameters, constraint audits and allocation comparisons. The Databricks App uses platform sign-in, the same model and persisted owner-scoped proposals. Publication records keep a partially completed pipeline run out of the current application view.

**Execution status:** the integrated application, ingestion, optimisation and export workflow have been tested locally. Databricks deployment code and integration tests are included; a successful workspace execution and live Databricks App URL have not yet been verified. This distinction must remain visible until actual run evidence replaces it.

## Why this model

Public data provides closure dates and demographics, but no observed meal-demand labels. We therefore use a transparent geospatial screen and mixed-integer allocation model, rather than manufacture a forecasting accuracy claim. Every proposal respects demand assumptions, capacity, geographic reach, maximum locality count and budget. A generated briefing is deterministic and tied to the saved plan; no paid LLM API is required.

Our fixed benchmark covers three dates, three budgets and three proximity thresholds: **15 unique scenarios**, all passing an independently reconstructed feasibility audit. Across the nine primary budget scenarios, the optimiser improved its **policy-weighted allocation objective by 0.3%–9.2%** over largest-demand-first. This measures a prioritisation difference under the same assumptions, not an observed increase in people helped. Tiny-instance exhaustive comparisons and adversarial tests check the mathematics and failure handling.

## Impact and what comes next

The first impact test is practical: can a coordinator prepare a better-evidenced closure plan in less time? A prospective pilot would measure preparation time, factual corrections, venue feasibility, uptake and operational cost. Census age, straight-line distance, missing non-hawker alternatives and unverified capacity remain important limits.

The commercial hypothesis is organisation-funded planning software, with residents never charged to view essential assistance information. A paid pilot and recurring price must be validated with buyers; we have not claimed customers, interviews or revenue. Commercial deployment would use paid infrastructure because Databricks Free Edition is for noncommercial use.

HawkerBridge's contribution is a clear source-to-decision workflow: identify a disruption, inspect uncertainty, test a constrained response and leave a reviewable record.

---

**Submitter checklist — remove this section from the public description.** Confirm Shivam's eligibility and fill in institution, course, year and email; do not infer current Singapore IHL enrollment. Attach the actual repository, deck, screenshots and recorded video links. For the final round, complete and verify the required Databricks run and replace the execution-status paragraph with precisely evidenced results. Do not replace it with an intended architecture presented as a completed deployment.
