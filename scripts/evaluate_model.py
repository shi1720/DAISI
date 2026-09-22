#!/usr/bin/env python3
"""Run a predeclared computational benchmark; never infer observed welfare outcomes.

Primary grid: 3 fixed closure dates × 3 budgets, 800-metre screening radius.
Reach sensitivity: the same 3 dates × 500/800/1200 metres at S$1,500.
The 3 overlapping configurations are evaluated once: 15 unique solves in total.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import statistics
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
import numpy as np  # noqa: E402
import scipy  # noqa: E402
from hawkerbridge.engine import MODEL_VERSION, PlanningEngine  # noqa: E402
from hawkerbridge.ingest import atomic_json, digest  # noqa: E402

DATES = ('2026-09-22', '2026-09-28', '2026-12-14')
BUDGETS = (1500, 3000, 6000)
RADII = (500, 800, 1200)
BASE_PARAMETERS = dict(radius_m=800, budget=1500, site_cost=300, meal_cost=4,
                       meals_per_site=150, max_sites=3, participation_rate=.05,
                       senior_weight=2, planning_areas=[], rescheduled_closure_ids=[])


def distance_metres(left: dict, right: dict) -> float:
    """Scalar spherical cosine rule, independent of the engine's vectorized haversine."""
    a, b = math.radians(left['lat']), math.radians(right['lat'])
    cosine = math.sin(a) * math.sin(b) + math.cos(a) * math.cos(b) * math.cos(
        math.radians(left['lng'] - right['lng']))
    return 6_371_008.8 * math.acos(min(1.0, max(-1.0, cosine)))


def audit_plan(plan: dict) -> dict:
    """Reconstruct allocation invariants solely from the returned plan evidence."""
    params, summary = plan['assumptions'], plan['summary']
    zones = {z['id']: z for z in plan['analysis']['zones'] if z['newly_exposed'] and z['residents'] > 0}
    demands = {key: math.ceil(z['residents'] * params['participation_rate']) for key, z in zones.items()}
    violations = []
    assigned = defaultdict(int)
    spent_cents, weighted = 0, 0.0
    max_reach, max_load = 0.0, 0
    seen_sites = set()
    for site in plan['sites']:
        if site['zone_id'] in seen_sites:
            violations.append('duplicate_collection_locality')
        seen_sites.add(site['zone_id'])
        if site['zone_id'] not in zones:
            violations.append('collection_locality_outside_candidate_set')
        elif any(abs(site[key] - zones[site['zone_id']][key]) > 1e-7 for key in ['lat', 'lng']):
            violations.append('collection_coordinates_do_not_match_candidate')
        load = 0
        for allocation in site['allocations']:
            count, key = allocation['meals'], allocation['zone_id']
            if not isinstance(count, int) or count < 1:
                violations.append('nonpositive_or_noninteger_meals')
            if key not in zones:
                violations.append('allocation_to_ineligible_zone')
                continue
            distance = distance_metres(zones[key], site)
            max_reach = max(max_reach, distance)
            if distance > params['radius_m'] + .01:
                violations.append('allocation_exceeds_reach')
            assigned[key] += count
            load += count
            weight = 1 + (params['senior_weight'] - 1) * zones[key]['seniors'] / zones[key]['residents']
            weighted += weight * count
        max_load = max(max_load, load)
        if not 0 < load <= params['meals_per_site']:
            violations.append('site_capacity_exceeded_or_empty')
        if load != site['meals']:
            violations.append('site_load_does_not_reconcile')
        site_cents = round(params['site_cost'] * 100) + load * round(params['meal_cost'] * 100)
        if round(site['cost'] * 100) != site_cents:
            violations.append('site_cost_does_not_reconcile')
        spent_cents += site_cents
    if summary['sites_selected'] != len(plan['sites']):
        violations.append('site_count_does_not_reconcile')
    if len(plan['sites']) > params['max_sites']:
        violations.append('site_limit_exceeded')
    if any(assigned[key] > value for key, value in demands.items()):
        violations.append('zone_demand_exceeded')
    if spent_cents > round(params['budget'] * 100):
        violations.append('budget_exceeded')
    if round(summary['spent'] * 100) != spent_cents:
        violations.append('total_cost_does_not_reconcile')
    if summary['total_meals'] != sum(assigned.values()):
        violations.append('total_meals_do_not_reconcile')
    if summary['estimated_demand'] != sum(demands.values()):
        violations.append('demand_does_not_reconcile')
    if summary['unmet_demand'] != sum(demands.values()) - sum(assigned.values()):
        violations.append('unmet_demand_does_not_reconcile')
    if abs(summary['weighted_benefit'] - weighted) > .00051:
        violations.append('weighted_objective_does_not_reconcile')
    if summary['weighted_benefit'] + .001 < summary['baseline_weighted_benefit']:
        violations.append('worse_than_baseline')
    return dict(feasible=not violations, violations=sorted(set(violations)),
                allocated_meals=sum(assigned.values()), cost_cents=spent_cents,
                max_site_load=max_load, max_assignment_distance_m=round(max_reach, 3),
                recomputed_weighted_benefit=round(weighted, 6),
                checks=['integer_allocations', 'candidate_sites', 'zone_demand', 'site_capacity',
                        'budget_cents', 'site_limit', 'geographic_reach', 'reported_totals',
                        'weighted_objective', 'not_worse_than_baseline'])


def run_evaluation(snapshot_path: Path) -> dict:
    raw = snapshot_path.read_bytes()
    snapshot = json.loads(raw)
    content = {key: value for key, value in snapshot.items() if key != 'manifest'}
    canonical = (json.dumps(content, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()
    if digest(canonical) != snapshot['manifest']['content_sha256']:
        raise ValueError('Snapshot content hash mismatch; rebuild or refresh before benchmarking')
    start = time.perf_counter()
    model = PlanningEngine(snapshot)
    initialization_ms = (time.perf_counter() - start) * 1000
    records = {}

    def run(day: str, budget: int, radius: int) -> str:
        identifier = f'{day}-sgd{budget}-r{radius}'
        if identifier in records:
            return identifier
        params = dict(BASE_PARAMETERS, date=day, budget=budget, radius_m=radius)
        start = time.perf_counter()
        plan = model.optimise(params)
        elapsed_ms = (time.perf_counter() - start) * 1000
        audit = audit_plan(plan)
        if not audit['feasible']:
            raise AssertionError(f"Benchmark {identifier} violated constraints: {audit['violations']}")
        records[identifier] = dict(id=identifier, parameters=params, elapsed_ms=round(elapsed_ms, 3),
                                  analysis_summary=plan['analysis']['summary'], summary=plan['summary'],
                                  baseline=plan['baseline'], constraint_audit=audit,
                                  sites=plan['sites'], uptake_sensitivity=plan['sensitivity'])
        return identifier

    primary_ids = [run(day, budget, 800) for day in DATES for budget in BUDGETS]
    reach_ids = [run(day, 1500, radius) for day in DATES for radius in RADII]
    primary = [records[key] for key in primary_ids]
    uplifts = [row['summary']['improvement_pct'] for row in primary]
    times = [row['elapsed_ms'] for row in records.values()]
    no_baseline = [row['id'] for row in primary if row['summary']['baseline_weighted_benefit'] == 0]
    return dict(
        evaluation_type='computational_scenario_benchmark',
        protocol_version='hawkerbridge-benchmark-1.0',
        generated_at=datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
        model_version=MODEL_VERSION,
        source_fingerprint=model.fingerprint,
        source_content_sha256=snapshot['manifest']['content_sha256'],
        snapshot_file_sha256=hashlib.sha256(raw).hexdigest(),
        engine_code_sha256=digest((ROOT / 'backend/hawkerbridge/engine.py').read_bytes()),
        evaluator_code_sha256=digest(Path(__file__).read_bytes()),
        data_as_of=snapshot['manifest']['fetched_at'],
        environment=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                         operating_system=platform.system(), machine=platform.machine()),
        protocol=dict(declared_dates=list(DATES), declared_budgets_sgd=list(BUDGETS),
                      declared_reach_metres=list(RADII), base_parameters=BASE_PARAMETERS,
                      primary_scenarios=primary_ids, reach_scenarios=reach_ids,
                      unique_scenarios=15, primary_count=9, reach_count=9, overlapping_count=3,
                      scope='All planning areas',
                      rationale='Fixed dates: acquisition day, next Monday cleaning wave, and December cleaning wave. '
                                'The grid is declared in source before execution; individual winners are not selected after scoring.'),
        summary=dict(all_feasible=True, unique_runs=len(records),
                     primary_improvement_pct_min=min(uplifts), primary_improvement_pct_max=max(uplifts),
                     primary_improvement_pct_median=statistics.median(uplifts),
                     primary_no_baseline_cases=no_baseline,
                     primary_optimal_within_tolerance=sum(r['summary']['solver_status'] == 'optimal' for r in primary),
                     solver_status_counts={status: sum(r['summary']['solver_status'] == status for r in records.values())
                                           for status in sorted({r['summary']['solver_status'] for r in records.values()})},
                     initialization_ms=round(initialization_ms, 3),
                     runtime_ms_min=min(times), runtime_ms_max=max(times),
                     runtime_ms_median=statistics.median(times)),
        scenarios=list(records.values()),
        limitations=[
            'These are scenario calculations and computational checks, not observed welfare, customer uptake or food-waste outcomes.',
            'Population is Census 2020; geographic representative points and straight-line distances are screening proxies.',
            'Meal uptake, costs, venue capacity and senior weighting are explicit assumptions.',
            'Improvement is in the policy-weighted allocation objective versus the largest-demand-first baseline, not a measured impact percentage.',
            'The primary uplift range summarizes all nine primary configurations, including zero improvement. Radius sensitivity is reported separately.',
            'A zero baseline produces a displayed zero improvement percentage; such cases are listed separately and percentage uplift is not meaningful for them.',
            'Solver optimality uses the configured 0.1% relative MIP-gap tolerance and five-second limit.',
            'Runtime is one local measurement per unique configuration after model initialization; it is not a production SLA or a Databricks performance measurement.',
            'Radius-based newly exposed counts need not change monotonically: increasing radius changes both baseline and current coverage.',
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=ROOT / 'data/processed/snapshot.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'data/processed/evaluation.json')
    args = parser.parse_args()
    try:
        result = run_evaluation(args.snapshot)
        atomic_json(args.output, result)
    except Exception as exc:
        print(f'Evaluation failed; previous evidence retained: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(result['summary'], indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
