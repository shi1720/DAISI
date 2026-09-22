"""Independent mathematical and data-boundary checks for the planning model.

Tiny synthetic fixtures are explicitly test-only. Their optima are enumerated rather
than calculated by another optimizer. Real-data tests check constraints, not social
outcomes that the source cannot observe.
"""
from __future__ import annotations

import copy
import itertools
import json
import math
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from hawkerbridge import engine as engine_module
from hawkerbridge.engine import PlanningEngine, haversine_matrix

ROOT = Path(__file__).resolve().parents[1]
DAY = '2026-09-28'


def tiny_snapshot(demands=(3, 2, 3), seniors=(0, 1, 3), spacing=.005):
    zones = [dict(id=f'z{i}', name=f'Test subzone {i}', planning_area='Test Area',
                  lat=1.3, lng=103.8 + spacing * i, residents=demand, seniors=seniors[i])
             for i, demand in enumerate(demands)]
    centres = [dict(id=f'c{i}', name=f'Test centre {i}', planning_area='Test Area',
                    lat=z['lat'], lng=z['lng'], address='Test-only fixture', food_stalls=1,
                    market_stalls=0) for i, z in enumerate(zones)]
    closures = [dict(id=f'closure-{i}', centre_id=c['id'], start_date=DAY, end_date=DAY,
                     kind='cleaning', source_text='Test-only fixture')
                for i, c in enumerate(centres)]
    return dict(centres=centres, demand_zones=zones, closures=closures,
                manifest={'closures_year': 2026, 'limitations': []})


def parameters(**overrides):
    return dict(date=DAY, radius_m=800, budget=8, site_cost=1, meal_cost=1,
                meals_per_site=3, max_sites=2, participation_rate=1,
                senior_weight=2, **overrides)


def great_circle_metres(a, b):
    """Independent scalar distance for reach assertions (spherical cosine rule)."""
    lat_a, lat_b = math.radians(a['lat']), math.radians(b['lat'])
    angle = (math.sin(lat_a) * math.sin(lat_b)
             + math.cos(lat_a) * math.cos(lat_b) * math.cos(math.radians(a['lng'] - b['lng'])))
    return 6_371_008.8 * math.acos(min(1, max(-1, angle)))


def brute_force_benefit(snapshot, params):
    """Enumerate every tiny integer allocation, including every site combination."""
    zones = snapshot['demand_zones']
    n = len(zones)
    demand = [math.ceil(z['residents'] * params['participation_rate']) for z in zones]
    weights = [1 + (params['senior_weight'] - 1) * z['seniors'] / z['residents'] for z in zones]
    best = 0.0
    row_options = []
    for i in range(n):
        candidates = []
        for assignments in itertools.product(range(demand[i] + 1), repeat=n):
            if sum(assignments) > demand[i]:
                continue
            if any(assignments[j] and great_circle_metres(zones[i], zones[j]) > params['radius_m'] + .01
                   for j in range(n)):
                continue
            candidates.append(assignments)
        row_options.append(candidates)
    for allocation in itertools.product(*row_options):
        site_loads = [sum(allocation[i][j] for i in range(n)) for j in range(n)]
        open_sites = sum(load > 0 for load in site_loads)
        if open_sites > params['max_sites'] or max(site_loads) > params['meals_per_site']:
            continue
        cost = open_sites * params['site_cost'] + sum(site_loads) * params['meal_cost']
        if cost > params['budget'] + 1e-9:
            continue
        score = sum(sum(allocation[i]) * weights[i] for i in range(n))
        best = max(best, score)
    return best


def assert_feasible(plan):
    params = plan['assumptions']
    affected = {z['id']: z for z in plan['analysis']['zones']
                if z['newly_exposed'] and z['residents'] > 0}
    demand = {key: math.ceil(z['residents'] * params['participation_rate']) for key, z in affected.items()}
    assigned = defaultdict(int)
    expected_cost = 0
    assert len(plan['sites']) <= params['max_sites']
    assert len({s['zone_id'] for s in plan['sites']}) == len(plan['sites'])
    for site in plan['sites']:
        assert site['zone_id'] in affected
        assert 0 < site['meals'] <= params['meals_per_site']
        assert sum(a['meals'] for a in site['allocations']) == site['meals']
        for allocation in site['allocations']:
            key = allocation['zone_id']
            assert key in affected
            assert isinstance(allocation['meals'], int) and allocation['meals'] > 0
            assigned[key] += allocation['meals']
            assert great_circle_metres(affected[key], site) <= params['radius_m'] + .01
        expected_cost += round(params['site_cost'] * 100) + site['meals'] * round(params['meal_cost'] * 100)
    for key, meals in assigned.items():
        assert meals <= demand[key], 'A zone must not receive duplicate demand through overlapping sites'
    assert expected_cost <= round(params['budget'] * 100)
    assert round(plan['summary']['spent'] * 100) == expected_cost
    assert plan['summary']['total_meals'] == sum(assigned.values())
    assert plan['summary']['estimated_demand'] == sum(demand.values())
    assert plan['summary']['unmet_demand'] == sum(demand.values()) - sum(assigned.values())
    assert plan['summary']['weighted_benefit'] + .002 >= plan['summary']['baseline_weighted_benefit']


@pytest.mark.parametrize('spacing,budget,max_sites,capacity,weight', [
    (.002, 8, 2, 3, 2),  # every point reaches every other point
    (.005, 8, 2, 3, 2),  # chain graph: one central site reaches both ends
    (.020, 8, 2, 3, 2),  # isolated sites
    (.005, 4, 1, 3, 5),  # scarcity and senior preference
    (.005, 2, 2, 3, 2),  # only setup plus one meal affordable
    (.005, 1, 2, 3, 2),  # setup alone cannot produce a meal
    (.005, 8, 0, 3, 2),  # explicit zero-site intervention
    (.005, 12, 3, 2, 2), # capacity bound rather than budget bound
    (.005, 8, 2, 3, 1),  # no senior preference
])
def test_integer_optimizer_matches_exhaustive_tiny_optimum(spacing, budget, max_sites, capacity, weight):
    snapshot = tiny_snapshot(spacing=spacing)
    params = parameters()
    params.update(budget=budget, max_sites=max_sites, meals_per_site=capacity, senior_weight=weight)
    result = PlanningEngine(snapshot).optimise(params)
    assert_feasible(result)
    assert result['summary']['weighted_benefit'] == pytest.approx(brute_force_benefit(snapshot, params), abs=.001)


@pytest.fixture(scope='module')
def real_snapshot():
    return json.loads((ROOT / 'data/processed/snapshot.json').read_text())


@pytest.mark.parametrize('day,radius,budget,participation', [
    ('2026-09-28', 800, 1500, .05),
    ('2026-12-14', 800, 1500, .05),
    ('2026-12-14', 200, 601.13, .001),
    ('2026-09-28', 1500, 10000, .1),
    ('2026-09-28', 3000, 0, 1),
])
def test_real_data_allocations_respect_all_constraints(real_snapshot, day, radius, budget, participation):
    result = PlanningEngine(real_snapshot).optimise(dict(date=day, radius_m=radius, budget=budget,
        site_cost=300.07, meal_cost=4.13, meals_per_site=150, max_sites=3,
        participation_rate=participation, senior_weight=2))
    assert_feasible(result)
    json.dumps(result, allow_nan=False)  # All-closed/empty cases must never emit Infinity.


def test_senior_policy_is_monotone_in_assigned_senior_share():
    snapshot = tiny_snapshot(demands=(3, 3, 3), seniors=(0, 1, 3), spacing=.02)
    shares = []
    for weight in [1, 2, 5]:
        params = parameters()
        params.update(senior_weight=weight, budget=5, max_sites=1)
        result = PlanningEngine(snapshot).optimise(params)
        assert_feasible(result)
        zone_by_id = {z['id']: z for z in snapshot['demand_zones']}
        shares.append(sum(a['meals'] * zone_by_id[a['zone_id']]['seniors'] /
                          zone_by_id[a['zone_id']]['residents']
                          for site in result['sites'] for a in site['allocations']))
    assert shares == sorted(shares)
    assert shares[-1] == 3  # Proxy person-equivalents, not observed senior recipients.


def test_budget_increases_cannot_reduce_exact_tiny_optimum():
    snapshot = tiny_snapshot()
    benefits = []
    for budget in [0, 1, 2, 4, 8, 10]:
        params = parameters()
        params['budget'] = budget
        result = PlanningEngine(snapshot).optimise(params)
        assert_feasible(result)
        benefits.append(result['summary']['weighted_benefit'])
    assert benefits == sorted(benefits)


def test_zero_food_markets_never_create_cooked_meal_access():
    snapshot = tiny_snapshot(demands=(10,), seniors=(3,))
    market = dict(snapshot['centres'][0], id='market-only', name='Test market', food_stalls=0, market_stalls=100)
    snapshot['centres'].append(market)  # Market stays open while only food centre closes.
    result = PlanningEngine(snapshot).analyse({'date': DAY, 'radius_m': 800})
    assert result['summary']['total_centres'] == 2
    assert result['summary']['newly_exposed_residents'] == 10
    assert result['zones'][0]['current_centre_id'] is None
    assert result['zones'][0]['current_distance_m'] is None


def test_real_zero_food_markets_do_not_enter_any_nearest_food_assignment(real_snapshot):
    markets = {c['id'] for c in real_snapshot['centres'] if c['food_stalls'] == 0}
    assert len(markets) == 3
    result = PlanningEngine(real_snapshot).analyse({'date': DAY})
    assert all(z['baseline_centre_id'] not in markets and z['current_centre_id'] not in markets
               for z in result['zones'])


def test_closure_boundaries_are_inclusive_and_old_works_do_not_close_current_centres():
    snapshot = tiny_snapshot(demands=(10,), seniors=(3,))
    snapshot['closures'][0].update(start_date='2026-09-27', end_date='2026-09-28')
    snapshot['closures'].append(dict(id='old-works', centre_id='c0', kind='works',
                                    start_date='2024-01-01', end_date='2024-12-31'))
    model = PlanningEngine(snapshot)
    observed = [model.analyse({'date': day})['summary']['closed_centres']
                for day in ['2026-09-26', '2026-09-27', '2026-09-28', '2026-09-29']]
    assert observed == [0, 1, 1, 0]


def test_moving_cleaning_cannot_cancel_overlapping_renovation():
    snapshot = tiny_snapshot(demands=(10,), seniors=(3,))
    snapshot['closures'].append(dict(id='works', centre_id='c0', kind='works',
                                    start_date='2026-09-01', end_date='2026-10-31'))
    model = PlanningEngine(snapshot)
    result = model.analyse({'date': DAY, 'rescheduled_closure_ids': ['closure-0']})
    assert result['summary']['closed_centres'] == 1
    assert [c['id'] for c in result['centres'][0]['active_closures']] == ['works']
    with pytest.raises(ValueError, match='cleaning'):
        model.analyse({'date': DAY, 'rescheduled_closure_ids': ['works']})
    with pytest.raises(ValueError, match='Unknown'):
        model.analyse({'date': DAY, 'rescheduled_closure_ids': ['not-in-source']})


def test_rescheduling_is_pure_and_only_changes_the_requested_scenario():
    snapshot = tiny_snapshot(demands=(10,), seniors=(3,))
    original = copy.deepcopy(snapshot)
    model = PlanningEngine(snapshot)
    moved = model.analyse({'date': DAY, 'rescheduled_closure_ids': ['closure-0']})
    assert moved['summary']['newly_exposed_residents'] == 0
    assert model.analyse({'date': DAY})['summary']['newly_exposed_residents'] == 10
    assert snapshot == original


def test_solver_outage_uses_a_feasible_baseline(monkeypatch):
    def unavailable(*_args, **_kwargs):
        raise RuntimeError('test solver outage')

    monkeypatch.setattr(engine_module, 'milp', unavailable)
    result = PlanningEngine(tiny_snapshot()).optimise(parameters())
    assert result['summary']['solver_status'] == 'baseline_fallback'
    assert result['summary']['total_meals'] == result['baseline']['total_meals']
    assert_feasible(result)


def test_infeasible_solver_vector_is_rejected(monkeypatch):
    def impossible(objective, **_kwargs):
        return SimpleNamespace(x=np.ones(len(objective)) * 999, status=0)

    monkeypatch.setattr(engine_module, 'milp', impossible)
    result = PlanningEngine(tiny_snapshot()).optimise(parameters())
    assert result['summary']['solver_status'] == 'baseline_fallback'
    assert_feasible(result)


def test_uncertain_uptake_is_not_reported_as_measured_waste():
    params = parameters()
    params['participation_rate'] = .5
    result = PlanningEngine(tiny_snapshot(demands=(30, 20, 30), seniors=(0, 5, 20))).optimise(params)
    for row in result['sensitivity']:
        assert row['matched_meals'] + row['potential_surplus_meals'] == result['summary']['total_meals']
        assert row['matched_meals'] + row['unmet_demand'] == row['estimated_demand']
    assert any('not an estimate of measured food waste' in text for text in result['limitations'])


def test_snapshot_is_frozen_against_caller_mutation():
    snapshot = tiny_snapshot(demands=(10,), seniors=(3,))
    model = PlanningEngine(snapshot)
    before = model.analyse({'date': DAY})
    snapshot['demand_zones'][0]['residents'] = 999999
    snapshot['centres'][0]['lng'] = 100
    snapshot['closures'].clear()
    after = model.analyse({'date': DAY})
    assert after == before, 'Cached distances and fingerprint must describe the same immutable input snapshot'


def test_pairwise_distance_handles_empty_sides_and_is_symmetric():
    points = tiny_snapshot()['demand_zones']
    distances = haversine_matrix(points, points)
    assert np.allclose(distances, distances.T)
    assert np.allclose(np.diag(distances), 0)
    assert haversine_matrix([], points).shape == (0, len(points))
    assert haversine_matrix(points, []).shape == (len(points), 0)


@pytest.mark.parametrize('day', ['2026-01-01', '2026-12-31'])
def test_calendar_does_not_imply_zero_closures_outside_source_year(day):
    result = PlanningEngine(tiny_snapshot()).analyse({'date': day})
    assert result['calendar']
    assert all(row['date'].startswith('2026-') for row in result['calendar']), (
        'A zero closure count outside the source calendar is missing data, not an observed zero'
    )


def test_direct_engine_rejects_dates_outside_source_schedule():
    model = PlanningEngine(tiny_snapshot())
    for day in ['2025-12-31', '2027-01-01']:
        with pytest.raises(ValueError, match='2026'):
            model.analyse({'date': day})


def test_post_solver_checks_include_binary_site_upper_bound(monkeypatch):
    # This vector passes the matrix rows by pretending the same facility opens twice.
    # It violates y <= 1, which a defensive boundary must check independently.
    monkeypatch.setattr(engine_module, 'milp', lambda *a, **k: SimpleNamespace(x=np.array([2., 6.]), status=0))
    snapshot = tiny_snapshot(demands=(10,), seniors=(3,))
    result = PlanningEngine(snapshot).optimise(parameters())
    assert result['summary']['solver_status'] == 'baseline_fallback'
    assert_feasible(result)


def test_density_has_no_false_zero_for_uninhabited_areas(real_snapshot):
    result = PlanningEngine(real_snapshot).analyse({'date': DAY})
    for row in result['area_ranking']:
        if row['residents'] == 0:
            assert row['hawker_centres_per_10000'] is None
        else:
            assert row['hawker_centres_per_10000'] == pytest.approx(
                10000 * row['food_centres'] / row['residents'], abs=.00051
            )


def test_scope_limits_demand_but_keeps_cross_boundary_food_alternatives():
    snapshot = tiny_snapshot(demands=(10, 20), seniors=(3, 5), spacing=.003)
    for i, area in enumerate(['Area A', 'Area B']):
        snapshot['demand_zones'][i]['planning_area'] = area
        snapshot['centres'][i]['planning_area'] = area
    snapshot['closures'] = [snapshot['closures'][0]]  # Nearby centre in B is open.
    result = PlanningEngine(snapshot).analyse({'date': DAY, 'planning_areas': ['Area A']})
    assert [z['id'] for z in result['zones']] == ['z0']
    assert result['summary']['total_residents'] == 10
    assert result['summary']['total_centres'] == 1
    assert result['summary']['closed_centres'] == 1
    assert result['summary']['newly_exposed_residents'] == 0
    assert result['zones'][0]['current_centre_id'] == 'c1'
    assert result['calendar'][7]['closed_centres'] == 1


def test_scope_never_spends_on_out_of_scope_demand():
    snapshot = tiny_snapshot(demands=(10, 20), seniors=(3, 15), spacing=.003)
    for i, area in enumerate(['Area A', 'Area B']):
        snapshot['demand_zones'][i]['planning_area'] = area
        snapshot['centres'][i]['planning_area'] = area
    params = parameters()
    params['planning_areas'] = ['Area A']
    result = PlanningEngine(snapshot).optimise(params)
    assert_feasible(result)
    assert result['summary']['estimated_demand'] == 10
    assert all(s['planning_area'] == 'Area A' for s in result['sites'])
    assert {a['zone_id'] for s in result['sites'] for a in s['allocations']} == {'z0'}


def test_unknown_scope_is_rejected_and_empty_scope_means_all_areas():
    model = PlanningEngine(tiny_snapshot())
    with pytest.raises(ValueError, match='Unknown planning area'):
        model.analyse({'date': DAY, 'planning_areas': ['Imaginary area']})
    assert model.analyse({'date': DAY, 'planning_areas': []}) == model.analyse({'date': DAY})


def test_real_area_scope_summaries_reconcile_to_only_scoped_zones(real_snapshot):
    scope = ['Clementi', 'Bedok']
    model = PlanningEngine(real_snapshot)
    result = model.analyse({'date': DAY, 'planning_areas': scope})
    assert {z['planning_area'] for z in result['zones']} == set(scope)
    assert result['summary']['total_residents'] == sum(z['residents'] for z in real_snapshot['demand_zones']
                                                      if z['planning_area'] in scope)
    assert result['summary']['total_centres'] == sum(c['planning_area'] in scope for c in real_snapshot['centres'])
    assert len(result['area_ranking']) == 2


def test_new_exposure_is_a_loss_band_not_a_monotonic_radius_measure():
    snapshot = tiny_snapshot(demands=(10,), seniors=(3,))
    snapshot['centres'][0]['lng'] = 103.8054  # About 600 m from demand point; closes.
    snapshot['centres'].append(dict(snapshot['centres'][0], id='open-backup', lng=103.8090))
    model = PlanningEngine(snapshot)
    exposed = [model.analyse({'date': DAY, 'radius_m': radius})['summary']['newly_exposed_residents']
               for radius in [500, 800, 1200]]
    assert exposed == [0, 10, 0]
