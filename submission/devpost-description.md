## Inspiration

A hawker centre closes for cleaning or repairs. The notice tells residents when it will close. A community coordinator still has to work out which neighbourhoods lose a nearby option, where temporary support could go, and what the available budget can achieve.

That gap inspired HawkerBridge: a practical continuity desk for Singapore's community teams. It addresses **C3: KopilamAI**. The goal is to help a coordinator make a clear, reviewable decision before a familiar daily routine is disrupted.

## What it does

Pick a date, inspect scheduled closures and see which census subzones lose nearby hawker coverage. Compare a hypothetical cleaning-date change. Then enter a budget and explicit cost, capacity and participation assumptions to generate a meal-support proposal.

The most useful moment in our demonstration is simple. For **28 September 2026**, the archived NEA schedule lists **17 centre closures**. At an **800-metre straight-line threshold**, six subzones are flagged for investigation. With the stated assumptions, **S$1,500 plans 225 meals**. **S$3,000 plans 450**. Double the budget to **S$6,000**, and the result stays at **450**, with **S$2,700 allocated**. The limit is three localities with capacity for 150 meals each. More funding alone does not solve that constraint.

A coordinator can save a private proposal, inspect its assumptions, record review notes, and export a PDF brief, CSV or complete JSON record. The app does not book venues, move official closure dates or dispatch meals. Proposed localities and capacity require an operator's verification.

## How we built it

HawkerBridge combines five Singapore national open datasets: [NEA hawker centre closures and inventory](https://data.gov.sg/datasets/d_bda4baa634dd1cc7a6c7cad5f19e2d68/view), [SingStat Census 2020 subzone age counts](https://data.gov.sg/datasets/d_d95ae740c0f8961a0b10435836660ce0/view), [URA planning-area boundaries](https://data.gov.sg/datasets/d_4765db0e87b9c86336792efe8a1f7a66/view), [URA subzone boundaries](https://data.gov.sg/datasets/d_8594ae9ff96d0c708bc2af633048edfb/view) and [national waste statistics](https://data.gov.sg/datasets/d_daf568968ab40dc81e7b08887a83c8fa/view). Waste figures provide context, not a centre-level waste estimate.

The Python pipeline preserves source bytes, dates and checksums, normalises closure intervals, quarantines ambiguous dates and validates geographic joins. A completed Databricks serverless Lakeflow Job published Bronze/Silver/Gold Delta tables under Unity Catalog and recorded nine scenario comparisons in MLflow. All twelve publication quality checks passed. Three tabular sources were fetched live; two URA geometry archives were reused with their original dates and verified checksums.

A transparent geospatial screen feeds a mixed-integer allocation model using SciPy and HiGHS. It respects budget, setup costs, meal costs, capacity, geographic reach and a declared senior-priority weight. React, TypeScript and Leaflet provide the interface; FastAPI serves the same planning engine and exports.

The public interface is available at [hawkerbridge-sg.web.app](https://hawkerbridge-sg.web.app), with Firebase Authentication, Cloud Firestore and a Python API on Cloud Run in Singapore. Private proposals survive application instances. Server-verified sessions, owner checks, optimistic edit revisions and resumable deletion protect the workflow. The application checks source and model fingerprints before displaying cloud execution evidence.

**Release status:** Databricks execution and hosted HTTP acceptance are verified. The public release passed managed sign-in, owner isolation, the 225/450/450 budget comparison, exports, CSRF/origin protection and stale-edit rejection. A saved account and proposal survived a container rollout, after which the test account was deleted. The final hosted browser journeys and video review are still in progress. [Databricks evidence](https://github.com/shi1720/DAISI/blob/main/data/processed/databricks-publication.json), [hosted acceptance](https://github.com/shi1720/DAISI/blob/main/output/hosted-smoke.json), [rollout persistence](https://github.com/shi1720/DAISI/blob/main/output/hosted-restart-smoke.json)

## Challenges we ran into

The data describes centres and census areas, not observed meal demand. We could not honestly train a hunger predictor or claim that every flagged resident needs support. The screen therefore uses subzone representative points and clearly labelled participation assumptions. Census 2020 totals are historical area counts, and straight-line distances are not accessible walking routes.

Closure records also contain unknown dates and staggered works. We preserve these in quarantine instead of silently treating them as confirmed open. Geographic scope must retain relevant alternatives across planning-area boundaries. Saved proposals must preserve their own source evidence, even when the active data changes.

Moving from a local app to public hosting exposed another practical challenge: accounts and plans must survive server restarts and remain private across users. That required durable managed authentication and storage, explicit session handling, and tests against the hosted service.

## Accomplishments that we're proud of

We built a complete source-to-decision workflow with reproducible public data, constrained allocation, saved proposals and usable exports. The model explains when money helps and when capacity is the real constraint.

The local robustness benchmark covers **15 unique scenarios** on the published snapshot, all passing an independently reconstructed feasibility audit. Across its nine primary budget scenarios, the policy-weighted objective improves **0.3% to 9.2%** over a largest-demand-first baseline. Tiny-instance exhaustive checks and adversarial tests examine the mathematics and failure handling.

The **nine actual Databricks evaluations are a separate set**: 22 September, 5 October and 14 December, each at S$600, S$1,500 and S$3,000, with 800-metre reach. Their policy-weighted objective improvement is **2.8% to 9.2%**. The September 28 demonstration is an API recomputation using the published data. These are model comparisons under stated assumptions, not observed meal demand, predictive accuracy or measured social impact.

## What we learned

A useful planning tool must make uncertainty visible at the point of decision. A convincing map alone is not enough. The coordinator needs to know which dates are uncertain, what a population count means, why a proposal stops growing, and which facts still need local verification.

We also learned that commercial value depends on a recurring operational task. Public data and an optimiser alone are easy to copy. Verified venue capacity, trustworthy records and integration into a coordinator's workflow would have to earn repeat use.

## What's next for HawkerBridge

The next step is one operator and one scheduled closure. A four-to-six-week pilot would compare preparation time, factual omissions, venue feasibility, uptake and cost with the existing process. A proposed 30% preparation-time reduction is a pilot target, not an achieved result.

Our buyer hypothesis is an estate operator or funded community organisation managing repeated disruptions. We would test a **S$1,000 scoped pilot** and a **S$250 to S$500 monthly organisation subscription**. These are pricing hypotheses; there are no claimed customers, interviews, partnerships or revenue. Residents would not pay for essential assistance information. Commercial operation requires suitable paid infrastructure.

**Project owner: Shivam Gupta.** Shivam initiated the brief, set the product goals and owns the project. Research, implementation, testing and presentation preparation used AI assistance. Sources, software and visual credits are documented in the [repository](https://github.com/shi1720/DAISI).

## Testing instructions

Open [hawkerbridge-sg.web.app](https://hawkerbridge-sg.web.app) and select **Explore as a guest**. No API key or account is required. Select **28 September 2026**, **All Singapore** and **800 m**. Inspect the closure list and map, then open **Continuity planner**.

Keep the displayed assumptions: 5% participation, S$4 per meal, S$300 locality setup, at most three localities and 150 meals per locality. Generate proposals at S$1,500, S$3,000 and S$6,000. Expected planned meals are **225, 450 and 450**, with costs of S$1,500, S$2,700 and S$2,700. The capacity ceiling explains why more budget does not add meals.

Save a draft, edit its coordination notes and export PDF, CSV or JSON. Review the checklist without asserting any real venue verification. Open **Evidence & methods** to inspect the completed Databricks publication, twelve quality checks, nine cloud scenarios, five source records and the separate fifteen-case local benchmark. For persistent access across devices, create an account using your own email and password. Guest workspaces are temporary.

See [full testing instructions](https://github.com/shi1720/DAISI/blob/main/submission/testing-instructions.md) for cleaning-date comparisons, mobile checks and expected limitations.
