# HawkerBridge: opportunity and evidence

Research checked 22 September 2026. Commercial assumptions below are unvalidated. No stakeholder interviews, partnerships, pilots or customer commitments are claimed.

## Decision

Build **HawkerBridge**, a closure continuity desk for **C3  -  KopilamAI**. The operating question is: **When a hawker centre closes, which neighbourhoods lose nearby hawker access, and what practical support can a coordinator propose within a budget?**

The product turns a dated closure into a comparison, a budgeted collection proposal and a reviewable decision record. Town council planners can also test removing an adjustable cleaning event from the selected date to understand the possible benefit of staggering it. This is a counterfactual; the tool does not change any published closure schedule or dispatch assistance.

## Options considered

Scores are our decision aid, not an independent judge's assessment. Each is on a 1–5 scale. Weights follow Round 1: impact 30%, originality 30%, technical feasibility 25%, clarity 15%. These scores assess the proposed product approach, not the worth of the social problem.

| Approach | Impact | Originality | Feasibility | Clarity | Weighted / 5 | Main concern |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| C3 closure continuity desk | 4.5 | 4.5 | 4.5 | 5.0 | 4.58 | Buyers and intervention demand need validation |
| B1 community heat response | 4.5 | 3.5 | 3.5 | 4.5 | 3.95 | Official advisories exist; station weather cannot establish indoor risk |
| C2 mobility access planning | 4.0 | 3.5 | 3.5 | 4.0 | 3.73 | Routing and barrier-free coverage are harder than proximity maps |
| A1 isolation prioritisation | 4.5 | 3.0 | 3.0 | 4.0 | 3.60 | No personal outcome labels; incumbent outreach already uses analytics |

The [participant guide](https://daisi.online/guide) explicitly includes food access, hawker closures and social vulnerability in C3. Final-round execution should emphasise measurable pipeline quality, usable decisions and honest limitations. A polished map is insufficient on its own.

## Evidence for a real workflow

[NEA's closure announcements](https://www.nea.gov.sg/our-services/hawker-management/announcements) assign cleaning and repairs of HDB-owned centres to the respective town councils; NEA handles MSE-owned centres. This makes the planner and closure schedule a defensible workflow hypothesis. Published examples at research time include Clementi West Street 2 Block 726 (14 September–27 December 2026) and Lorong 7 Toa Payoh Block 22 (14 September–13 December 2026). The app must use its current ingested snapshot, rather than treating these examples as permanent facts.

The [official NEA dataset](https://data.gov.sg/datasets/d_bda4baa634dd1cc7a6c7cad5f19e2d68/view) had 123 records and 27 fields at research time, including coordinates, food-stall counts and closure intervals. It also exposes genuine engineering problems: unknown dates, missing data, split-block exceptions in remarks, old repair dates retained within a current-year feed, and overlapping periods. Preserve and report uncertainty instead of silently converting it to an open centre.

[NEA's socially-conscious enterprise model](https://www.nea.gov.sg/our-services/hawker-management/socially-conscious-enterprise-hawker-centres/sehcs--serving-communities-through-affordable-varied-food-and-activities) gives another possible buyer: operators receive a management fee and are assessed on affordability, food mix and community outcomes. This establishes an operating context, not willingness to purchase our software.

## Competition and honest differentiation

| Existing service | What it already does | HawkerBridge's intended additional decision |
| --- | --- | --- |
| [NEA myENV](https://www.nea.gov.sg/docs/default-source/myenv/myenv-app-user-guide-for-top-features---21-feb-2025.pdf) | Follow a hawker centre and receive closure notifications | Compare area exposure and plan mitigations before disruption |
| [SGMakan](https://sgmakan.com/hawker-closures) | Publish hawker closure dates | Budget, compare and save a continuity proposal |
| [SG Hawker Closure](https://sghawkerclosure.live/) | Advertise closures and nearby alternatives | Demographic exposure and constrained support allocation |
| [SG Toolkit](https://sgkit.app/index.html) | Retrieve NEA closure status | An accountable coordinator workflow |

We did not identify an equivalent public product in the searches undertaken. That is not proof of being first or unique. Do not claim that closure detection, a hawker map, or a chatbot over public data is novel.

The defensible difference is **dated counterfactual planning under resource constraints**, with source lineage, uncertainty and a coordinator's review. Public data is not a moat. Potential defensibility would come later from permissioned operational outcomes, actual intervention capacity, coordinator corrections and integration with an organisation's processes.

## Proposed operating journey

1. A coordinator selects a closure date and proximity assumption.
2. The app compares ordinary hawker coverage with coverage during scheduled closures.
3. The coordinator inspects affected subzones, source dates and uncertainty.
4. A scenario removes an adjustable cleaning event from that date to test the value of staggering. It is not a full rescheduling recommendation: operational constraints and the replacement date need separate verification.
5. For closures that remain, the coordinator enters a daily budget, cost assumptions, possible participation and capacity.
6. The optimiser compares an allocation with a simple largest-demand-first baseline.
7. The coordinator saves a draft and exports its assumptions, proposed localities and source fingerprint for field verification.

No resident needs to install an app. No personal beneficiary records are required for the challenge build. A saved or reviewed proposal is not approval by an agency and is not an instruction to a meal operator.

## Commercial hypothesis and economics

The first customer hypothesis is an estate operator or funded multi-site community organisation. Residents and individual hawkers should not be the first paying customers. The buyer value must be demonstrated as coordinator time saved, avoidable support expenditure, or a documented improvement in access planning.

**Unvalidated pricing experiment:** S$1,000 for one closure-planning pilot, creditable against a S$250–500 monthly organisation subscription. These are proposed prices, not market evidence. Subscription economics depend on repeat usage beyond infrequent major renovations. Annual and quarterly cleaning planning could support reuse. Singapore hawker closures alone are a small initial market; a larger business would need evidence that the workflow generalises to other neighbourhood service disruptions.

**Illustrative break-even only:** at a S$300 monthly subscription and an assumed S$30 fully loaded coordinator hour, the software needs to save ten staff-hours per month before considering implementation or verification costs. Neither input has been validated with a buyer. Track measured preparation time during pilots instead of putting this illustration forward as ROI already achieved.

For context, [AIC lists Meals on Wheels](https://www.aic.sg/Care-Services/Meals-on-Wheels) from S$4 per meal before subsidies. This is not a supplier quote for temporary collection or pop-up provision. [TOUCH's programme](https://www.touch.org.sg/get-assistance/seniors/meals-on-wheels-mow.html) involves needs assessment, service boundaries, dietary requirements and licensed catering; [its volunteer workflow](https://www.touch.org.sg/get-involved/volunteer/meals-on-wheels.html) includes collection points and walking or driving routes. Real deployment must verify those capacities with operators.

An important caution is [Food from the Heart's Project Belanja!](https://www.foodfromtheheart.sg/project-belanja/): its app-driven neighbourhood hawker meal programme has been phased out since 2024 to redirect resources and improve efficiency. A meal app is not automatically commercially or operationally sustainable. HawkerBridge proposes planning support for existing operators, not a new delivery marketplace.

### What must be validated before a commercial claim

- At least three coordinator interviews demonstrating the current planning process and its frequency.
- One consented observation of closure planning, including time spent and tools used.
- A funded pilot or credible purchase commitment; expressions of interest are not revenue.
- Locally verified alternative food supply and candidate collection venues.
- Actual demand and participation measurements under appropriate consent and governance.
- Production hosting cost, support burden and procurement lead time.

## Data and modelling boundaries

- We estimate **potential exposure to reduced hawker proximity**, not hunger, food insecurity, vulnerability of a named individual or actual reliance on one centre.
- A hawker-only inventory omits coffee shops, food courts, home cooking and delivery. Never label a hawker coverage gap a food desert without wider evidence.
- Food-stall counts are descriptive, not measured meal capacity or opening hours.
- Distances are a proximity screen unless separately routed. [OneMap's routing API](https://www.onemap.gov.sg/apidocs/routing) requires authentication and provides walk, drive, cycle and public-transport routing. Proximity does not establish a step-free route.
- Subzone or planning-area demographics cannot be silently represented as observed block populations.
- Participation, meal budgets, capacity and collection suitability are editable planning assumptions. Do not convert proposed meals into people actually helped.
- Do not infer site-level food waste from national waste tonnage. Waste benefits require operational measurement.
- There are no observed closure-demand outcome labels in the open dataset. A transparent geospatial model and constrained optimiser are appropriate; a model trained on manufactured labels would not establish predictive performance.

For comparison, [MSE already operates heat stress guidance](https://www.mse.gov.sg/latest-news/press-release-heat-stress-advisory/) and [AIC already uses data-driven analytics in senior outreach](https://www.aic.sg/wp-content/uploads/2026/01/Press-Release-SGO-partnerships.pdf). Avoid describing these sectors as devoid of existing analytics.

## Recommended judging evidence

Show one dated source-to-plan journey, demonstrate a malformed-date quality check, show measured optimiser results against the named baseline on the same assumptions, and change the budget or participation assumption live. Present any improvement as modelled within the stated scenario. The most defensible impact target is a pilot that measures planning time and verifies whether proposed coverage improvements occur.
