# HawkerBridge: questions worth asking

**1. What is original here? Closure maps already exist.**

Yes. NEA myENV, SGMakan and other public services already communicate closures and alternatives. Our contribution is the coordinator's next decision: compare the dated loss of nearby hawker access, test assumptions, allocate a constrained support budget and preserve an auditable proposal. We do not claim to have invented closure detection, geospatial analysis or mathematical optimisation, or to be the first product anywhere with this workflow.

**2. Why choose hawker closures instead of a larger national problem?**

It is a specific, understandable disruption with public dates, a bounded workflow and a concrete decision-maker. Cleaning and repairs create an opportunity to plan before an interruption occurs. A focused product lets us demonstrate source-to-plan reliability. It does not establish that hawker closures cause hunger or that this is the largest food-access problem in Singapore.

**3. Where is the AI? Why no forecasting model or chatbot?**

The substantive analytical work is geospatial exposure analysis and a mixed-integer decision model. It chooses an allocation under budget, capacity, reach and an explicit senior-priority policy. Public sources do not provide observed meal demand or outcome labels suitable for a validated forecast. Manufacturing labels or adding a chat interface would not improve that evidence. MLflow records the model's actual scenario evaluations; the plan brief is deterministic, so no LLM API is required.

**4. Census 2020 is old. Can you trust the exposure number?**

It is a reproducible screen using available subzone-level age counts, clearly labeled with its year. It is not a 2026 population estimate. Each whole subzone is represented by one point, which creates substantial aggregation error; straight-line distance is not an accessible walking route. We show threshold sensitivity and source years, and require local verification before allocating real services. Newer compatible small-area counts and better within-zone population information would improve the screen.

**5. Does “91,180 exposed residents” mean 91,180 people need meals?**

No. It is the Census 2020 population in six subzones whose representative points fall within 800 metres of a listed food centre before the scheduled closures and outside that threshold afterward on 28 September 2026. It does not observe anyone's reliance, route, income, appetite or alternative food supply. Other food outlets are omitted. We deliberately avoid equating this proxy with food insecurity.

**6. Are the meals, venues and four-dollar price real?**

They are editable planning assumptions, not booked capacity, supplier quotes or completed deliveries. The default 5% uptake converts exposure into assumed demand. Candidate localities are subzone points, not approved collection venues. For context, AIC advertises Meals on Wheels from S$4 before subsidies, but that service is not a quote for our proposed arrangement. An operator must verify cost, demand, safety, dietary needs, capacity and access before implementation.

**7. Does optimisation actually help, or just produce an impressive score?**

Across the complete nine-row primary benchmark, the policy-weighted objective improves by 0.3%–9.2% against largest-demand-first using identical assumptions and constraints. That can change prioritisation without increasing total meals. All 15 unique budget/reach scenarios passed an independent constraint audit, and tiny test instances were compared with exhaustive enumeration. These establish mathematical behaviour, not welfare benefit. The Sep 28 demo's strongest finding is simpler: a S$6,000 budget still buys only 450 planned meals when three 150-meal localities are the binding constraint.

**8. Why give seniors extra weight? Could that unfairly exclude others?**

It is a visible, adjustable policy parameter, not a learned vulnerability label. The default increases a zone's priority in proportion to its aggregate senior share; it does not identify or rank individual seniors. Coordinators can compare a neutral weighting and inspect changed allocations. Age alone is an incomplete basis for need, and an eventual operator policy must consider disability, income, dietary requirements and existing assistance using appropriately governed evidence.

**9. What happens when the public data is wrong or a refresh fails?**

Raw bytes and checksums are retained. The parser preserves source text, validates dates and joins, and quarantines TBC dates and ambiguous block-specific closures instead of inventing dates. Publication occurs after validation, and failed refreshes retain the last good snapshot. Data age and uncertainty remain visible. No system can infer that an unresolved centre is definitely open; the operator should confirm high-consequence closures with the relevant authority.

**10. Is this running on Databricks?**

Yes. The real serverless job completed successfully, published Bronze/Silver/Gold Delta tables and passed 12 quality checks. Its nine cloud scenarios were recorded in MLflow. Three tabular datasets were fetched live and two checksummed URA geometry archives were reused. The native Databricks App passes authenticated health, planning and evidence checks; anonymous access is denied. Its Delta store passed actual owner-isolation and concurrent-edit tests. The public Firebase application serves a verified export of the same publication so judges can try it without a workspace account. See the actual run, app and dashboard links in deployment-status.json and docs/databricks-verification.json. The 15-scenario local robustness benchmark is a separate protocol, not 15 claimed cloud runs.

**11. Who pays, and can this be commercially viable on free infrastructure?**

The proposed buyer is an estate operator or funded multi-site community organisation; the first experiment is a S$1,000 paid pilot followed by a S$250–500 monthly organisation subscription. Those are hypotheses, not validated willingness to pay. The measurable value would be planning time saved and more reliable coordination, with meal funding separate. Databricks Free Edition is noncommercial and has no SLA, so a commercial offering needs paid infrastructure. Support, procurement and founder time may dominate costs; there is no required per-request LLM cost, but operating the service is not free.

**12. What is the moat, and what would make you stop?**

Public data and a solver are not a moat. Repeatable operator workflows, verified capacities, permissioned feedback and useful integrations could become defensible only if a real customer adopts them. We have no claimed interviews, pilots, partnerships or revenue. We would narrow or stop this product if coordinators do not face a recurring planning burden, proposals cannot survive field verification, or willingness to pay is below the fully loaded cost of delivery. A technically correct demonstration does not settle those questions.

Evidence: [model evaluation](../docs/evaluation.md), [model limitations](../docs/model-review.md), [business assumptions](../docs/business-case.md), [deployment status](deployment-status.json), [NEA closure responsibilities](https://www.nea.gov.sg/our-services/hawker-management/announcements), [AIC meal-service context](https://www.aic.sg/Care-Services/Meals-on-Wheels), [Databricks Free Edition limits](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations).
