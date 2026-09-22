"""The evidence generator must reject tampered allocations, not merely report success."""
import copy
import importlib.util
from pathlib import Path

import pytest
from hawkerbridge.engine import PlanningEngine

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('evaluate_model', ROOT / 'scripts/evaluate_model.py')
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


@pytest.fixture
def real_plan():
    import json
    snapshot = json.loads((ROOT / 'data/processed/snapshot.json').read_text())
    return PlanningEngine(snapshot).optimise(dict(evaluation.BASE_PARAMETERS, date='2026-09-28'))


def test_feasibility_auditor_reconstructs_real_plan(real_plan):
    audit = evaluation.audit_plan(real_plan)
    assert audit['feasible']
    assert not audit['violations']
    assert audit['allocated_meals'] == 225
    assert audit['cost_cents'] == 150000


def test_feasibility_auditor_detects_double_demand_and_capacity_tampering(real_plan):
    altered = copy.deepcopy(real_plan)
    altered['sites'][0]['allocations'][0]['meals'] = 100000
    audit = evaluation.audit_plan(altered)
    assert not audit['feasible']
    assert 'site_capacity_exceeded_or_empty' in audit['violations']
    assert 'zone_demand_exceeded' in audit['violations']
    assert 'budget_exceeded' in audit['violations']


def test_feasibility_auditor_detects_fabricated_location(real_plan):
    altered = copy.deepcopy(real_plan)
    altered['sites'][0]['lat'] = 0
    audit = evaluation.audit_plan(altered)
    assert not audit['feasible']
    assert 'collection_coordinates_do_not_match_candidate' in audit['violations']
    assert 'allocation_exceeds_reach' in audit['violations']


def test_feasibility_auditor_detects_unearned_objective(real_plan):
    altered = copy.deepcopy(real_plan)
    altered['summary']['weighted_benefit'] *= 2
    audit = evaluation.audit_plan(altered)
    assert 'weighted_objective_does_not_reconcile' in audit['violations']
