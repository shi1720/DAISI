# HawkerBridge model review

Review date: 22 September 2026. Scope: `backend/hawkerbridge/engine.py`, the delivered official-data snapshot and the C3 brief. The adversarial test fixtures are explicitly synthetic and are used only to verify mathematics; product outputs use the recorded Singapore government data.

## Assessment

The allocation model is a defensible decision-support model. It solves a concrete constrained resource-allocation problem and compares against a feasible operational baseline. It does **not** predict individual hunger, measure spare hawker capacity or establish that a proposed venue is available. Its value is in making preparation choices inspectable: which localities lose a nearby listed food centre under a published closure schedule, how an assumed support budget can be allocated, and how the plan changes with assumptions.

The appropriate description is **geospatial screening plus mixed-integer optimization**. Calling the demographic inputs an observed meal-demand dataset, reporting “prediction accuracy” against a constructed score, or presenting the weighted benefit as residents demonstrably helped would be incorrect.

## Mathematical contract

For each newly exposed subzone `i`, assumed daily demand is `d_i = ceil(residents_i × participation_rate)`. Each subzone has policy weight `w_i = 1 + (senior_weight − 1) × senior_share_i`.

A candidate collection locality `j` is the subzone's geographic representative point. An integer `x_ij` allocates meals to subzone `i` from locality `j`; binary `y_j` opens that locality. A pair is permitted only when the great-circle distance is within the chosen radius.

The model maximizes `sum(w_i × x_ij)`, with a tiny penalty favouring fewer sites in otherwise equivalent solutions, subject to:

- Every zone receives no more than its assumed demand: `sum_j x_ij <= d_i`.
- Each open locality stays within assumed meal capacity: `sum_i x_ij <= capacity × y_j`.
- Setup costs plus meal costs stay within the daily budget, using integer cents.
- Open localities do not exceed `max_sites`.
- Assignments and site variables satisfy non-negativity, integrality and variable upper bounds.

The optimization objective rewards assigned meals in areas with a greater older-resident share. It does not identify the age of an actual recipient. Increasing `senior_weight` is a policy change, not a change in observed need.

The HiGHS solve has a five-second time limit and 0.1% relative MIP-gap tolerance. “Optimal” should therefore be read as solved within the configured tolerance; do not claim an exhaustive proof of the global optimum for every production instance. A feasible incumbent or a constraint-safe greedy baseline preserves functionality if optimization times out or fails.

## Verification

`tests/test_engine_adversarial.py` independently enumerates all integer allocations for nine tiny scenarios. It covers complete, chain and disconnected reach graphs; scarce budget; zero sites; capacity limits; and senior weighting. The oracle uses enumeration, not a second call to the same solver. The model's objective agrees with these exhaustive optima.

Additional tests use real data for five date/radius/budget/uptake combinations and verify that:

- Meals are nonnegative integers, reach only eligible zones, and obey each locality's capacity.
- Overlapping collection localities cannot double-count a zone's demand.
- Costs cannot exceed the budget, including non-round cent amounts.
- The reported totals, unmet demand and spent amount reconcile with allocations.
- The chosen weighted benefit is no worse than the feasible baseline.
- Tiny exact solutions obey expected budget and senior-preference monotonicity.
- Date intervals are inclusive; retained 2024 works never become 2026 closures.
- Moving a cleaning interval does not remove overlapping renovation works.
- Scenario calls leave source data unchanged; caller mutation cannot change cached engine inputs.
- All-food-centres-closed cases emit null distance, never JSON Infinity.
- Solver outages and obviously infeasible solver vectors fall back safely.
- Fixed-plan sensitivity reconciles assumed demand, matched meals, unmet demand and potential surplus.

## Review findings and corrections

1. **Zero-food markets:** Three of the 123 NEA-listed facilities contain zero listed cooked-food stalls: Redhill Market, Telok Blangah Market and Ayer Rajah Market. They belong in the inventory but must not count as a cooked-meal alternative. The engine now excludes them from food-access distance calculations and exposes their eligibility. There are 120 food-access-eligible centres.
2. **Snapshot aliasing:** The original constructor kept references to the caller's mutable lists while caching distances and fingerprint. It now binds centre, zone, closure and manifest inputs to its own deep copy. The mutation regression test passes.
3. **Unsupported years:** Direct engine calls now reject dates outside the snapshot's closure year, in addition to API validation. This prevents a missing future schedule being interpreted as no closures.
4. **Density criterion:** Area results now expose eligible hawker centres per 10,000 residents. Uninhabited areas return null density, not a misleading zero. Denominators use summed rounded subzone observations, so small differences from published planning-area totals are expected.
5. **Calendar boundary  -  corrected:** The 35-day calendar originally crossed into an unsupported adjacent year and emitted zero closure counts there. It is now restricted to the source year. Regression tests for 1 January and 31 December pass.
6. **Solver variable bounds  -  corrected:** The original post-solver check validated matrix rows and non-negativity but did not independently check variable upper bounds. A deliberately corrupted test vector `y=2, x=6` passes the rows for one candidate with capacity 3, demand 10 and budget 8, but is not a valid binary facility decision. Real HiGHS should not produce this vector; checking bounds is defensive hardening of the solver boundary. The engine now checks variable upper bounds; the regression test confirms rejection and a feasible fallback.

All review findings above are resolved. Scope tests additionally verify that selected planning areas restrict demand and spending while nearby food centres across administrative boundaries remain valid alternatives. Unknown scopes are rejected. Run `.venv/bin/python -m pytest tests/test_engine_adversarial.py tests/test_evaluation.py -q` for current acceptance status. The independent evidence auditor also detects deliberately inflated allocations, fabricated coordinates and unearned objective scores.

The fixed protocol and measured results are documented in [evaluation.md](evaluation.md), with machine-readable results in `data/processed/evaluation.json`. Compare its source fingerprint to the active model before displaying evidence after a refresh.

## Interpretation limits and operational acceptance

- **Census year:** Demographics are Census 2020, with rounding. They are not a 2026 count or forecast. Whole-subzone exposure is an aggregate screening estimate.
- **Geography:** Representative points are not household locations or population-weighted centres. Straight-line distance is not walking time, wheelchair accessibility or a confirmed route. A 799-to-801-metre change can change the radius-based binary label; inspect sensitivity before prioritizing.
- **Providers:** Coffee shops, food courts, home cooking, delivery and informal alternatives are absent. Losing a listed hawker option does not establish food insecurity.
- **Closure quality:** TBC dates and staggered block closures are quarantined. A missing resolved closure is not evidence that a centre is open. The 2026 feed is a present schedule with selected earlier works, not a complete history of permanent closures.
- **Demand and capacity:** Participation, setup cost, meal price and capacity are transparent editable assumptions. Candidate sites are geographic suggestions, not approved premises. A coordinator must verify demand, venue, accessible route and supplier before operating.
- **Waste:** National annual waste totals give context. “Potential surplus meals” is a scenario consequence under lower uptake, not measured food waste or a causal reduction claim. Sensitivity holds the original allocation fixed rather than re-optimizing it.
- **Baseline:** “Largest demand first” is an intentionally simple comparator. Improvement over it demonstrates the consequence of the chosen objective; it does not prove superiority to an experienced coordinator or establish real-world impact.
- **Site demand display:** A subzone can receive allocations from multiple sites, without exceeding total demand. Site-level “estimated demand” describes overlapping receiving catchments and must not be added across sites. The plan-level estimated demand is the non-overlapping total.

A credible pilot should first compare recommended localities against coordinator review, confirm feasible venues and providers, and record actual collection, unmet requests and surplus. Only that evidence can validate service outcomes. Until then, report the operational value as an auditable preparation scenario and a tested allocation engine.
