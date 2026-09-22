# Computational evaluation and provenance

Generated 2026-09-22T04:34:42.876701Z. This is a fixed scenario benchmark and a mathematical feasibility audit. It is **not an observed welfare evaluation, user trial, demand forecast or model accuracy claim**.

## Reproduce

```bash
.venv/bin/python scripts/evaluate_model.py
.venv/bin/python -m pytest tests/test_engine_adversarial.py tests/test_evaluation.py -q
```

The script reads `data/processed/snapshot.json` and atomically publishes `data/processed/evaluation.json`. If any independently reconstructed constraint fails, it stops and retains the previous evidence file. The artifact records every configuration, allocation, audit, solver status and measured runtime, alongside snapshot, engine-code and evaluator-code hashes.

Protocol version: `hawkerbridge-benchmark-1.0`. Model: `hawkerbridge-1.0.0`.

Source content SHA-256: `5b7aaf83b6cdc25fb4262eaa99ee116925d4c5ab8a634647f46f35d21acde783`.

The source fingerprint, snapshot-file hash and exact code hashes are in the JSON. Re-run after changing the model or snapshot. Evidence should be marked stale if its source fingerprint does not match the active engine. A rebuild may change the full snapshot fingerprint because provenance timestamps are included even when underlying content is unchanged.

## Fixed protocol

The primary grid contains all combinations of 22 September, 28 September and 14 December 2026 with daily budgets of S$1,500, S$3,000 and S$6,000. Radius sensitivity uses 500, 800 and 1,200 metres on the same three dates at S$1,500. The overlapping 800-metre configurations are reused, yielding **15 unique solves**, nine primary rows and nine reach-sensitivity rows. Every row is reported; this is an exploratory fixed grid, not a preregistered statistical study or held-out prediction evaluation.

All runs use islandwide scope, no hypothetically moved closures, 5% assumed participation, S$300 setup per collection locality, S$4 per meal, capacity 150 meals per locality, at most three localities, and senior-policy weight 2. These are editable planning assumptions, not vendor quotes or measured uptake. All source demographics are Census 2020.

## Results

All 15 unique runs passed the independent feasibility audit. All solves reported optimality within the configured 0.1% MIP-gap tolerance. The primary nine configurations improved the **policy-weighted allocation objective** by 0.3%–9.2% versus the largest-demand-first baseline; the median was 8.8%. No primary configuration had a zero baseline. This is not a percentage increase in residents actually helped.

| Date | Budget S$ | Exposed subzones | Assumed meals requested | Planned meals | Spent S$ | Baseline weighted score | Optimized weighted score | Objective uplift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-09-22 | 1,500 | 14 | 19,520 | 225 | 1,500 | 251.190 | 271.310 | 8.0% |
| 2026-09-22 | 3,000 | 14 | 19,520 | 450 | 2,700 | 498.537 | 542.205 | 8.8% |
| 2026-09-22 | 6,000 | 14 | 19,520 | 450 | 2,700 | 498.537 | 542.205 | 8.8% |
| 2026-09-28 | 1,500 | 6 | 4,561 | 225 | 1,500 | 266.466 | 271.003 | 1.7% |
| 2026-09-28 | 3,000 | 6 | 4,561 | 450 | 2,700 | 537.275 | 538.909 | 0.3% |
| 2026-09-28 | 6,000 | 6 | 4,561 | 450 | 2,700 | 537.275 | 538.909 | 0.3% |
| 2026-12-14 | 1,500 | 22 | 25,473 | 225 | 1,500 | 251.190 | 273.258 | 8.8% |
| 2026-12-14 | 3,000 | 22 | 25,473 | 450 | 2,700 | 498.537 | 544.261 | 9.2% |
| 2026-12-14 | 6,000 | 22 | 25,473 | 450 | 2,700 | 498.537 | 544.261 | 9.2% |

The model exposes a practical constraint: increasing the budget from S$3,000 to S$6,000 adds no meals under the fixed limit of three localities at 150 meals each. Capacity caps the intervention at 450 meals. A plan spends S$2,700 at that ceiling, leaving S$3,300 unused from the larger budget. More funding alone does not expand this scenario; a coordinator needs more verified venue capacity or a different delivery arrangement. The model does not claim those extra venues exist.

The optimized and baseline solutions may provide the same number of meals while directing them to zones with different demographic weights. Objective improvement is therefore a prioritization difference, not necessarily a volume increase.

## Radius sensitivity

The values below are aggregate residents in subzones whose representative point had a listed food centre inside the selected radius before closures, and lacks one inside that radius after closures. They do not count individual residents' routes or establish hunger.

| Date | Radius m | Newly exposed residents, proxy | Of these aged 65+, proxy | Exposed subzones |
|---|---:|---:|---:|---:|
| 2026-09-22 | 500 | 357,890 | 48,860 | 17 |
| 2026-09-22 | 800 | 390,350 | 47,600 | 14 |
| 2026-09-22 | 1200 | 431,570 | 52,980 | 13 |
| 2026-09-28 | 500 | 208,500 | 44,160 | 13 |
| 2026-09-28 | 800 | 91,180 | 17,120 | 6 |
| 2026-09-28 | 1200 | 186,420 | 33,390 | 6 |
| 2026-12-14 | 500 | 469,530 | 79,160 | 20 |
| 2026-12-14 | 800 | 509,350 | 72,560 | 22 |
| 2026-12-14 | 1200 | 534,280 | 77,230 | 22 |

Newly exposed counts need not decrease with a larger radius. Radius affects **both** the baseline and remaining access sets. A zone with its original centre 600 metres away and an alternative 1,000 metres away is outside the baseline at 500 metres, newly exposed at 800 metres, and covered at 1,200 metres. The adversarial tests include exactly this example. Treat the radius as a policy assumption and inspect the sensitivity rather than treating one threshold as ground truth.

## Constraint audit and timing

The auditor reconstructs demand from residents and participation, then checks integer allocations, eligible candidate sites, genuine candidate coordinates, individual zone demand, per-site capacity, integer-cent cost, total budget, maximum site count, geographic reach, objective reconciliation and comparison to baseline. Test-only corruptions demonstrate that it rejects inflated allocations, fabricated locations and invented objective improvements. Baseline failure and solver-boundary tests are covered separately by the engine suite.

On this one local run, model initialization took 39.476 ms. Each unique optimize-plus-analysis call took 4.230–19.652 ms (median 11.822 ms). Environment: Python 3.12.14, NumPy 2.5.3, SciPy 1.18.1, Darwin arm64. These are single local measurements after initialization, not a Databricks measurement, load test or service-level promise. Repeated runs and different environments will vary.

## What remains unvalidated

No operator capacity, collection venue, individual need, uptake, meal affordability, waste reduction, accessible walking route or welfare outcome has been observed. Coffee shops and other meal alternatives are omitted. Source dates marked TBC or ambiguous by block are quarantined. Proposed localities require human verification. Pilot measurements—not a higher optimization score—are needed before making real-world impact claims. See [model-review.md](model-review.md) for the complete interpretation and acceptance review.
