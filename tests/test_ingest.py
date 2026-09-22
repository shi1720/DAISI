"""Data contracts, unknown-date handling and fail-safe publication tests."""
import copy
import json
from pathlib import Path

import pytest
from hawkerbridge import ingest

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw' / 'baseline-20260922'


@pytest.fixture
def source_row():
    return json.loads((RAW / 'closures.json').read_text())['result']['records'][0]


def test_verified_baseline_joins_all_real_census_subzones():
    snapshot = ingest.build_snapshot(RAW)
    assert len(snapshot['centres']) == 123
    assert len(snapshot['demand_zones']) == 332
    assert len(snapshot['boundaries']['features']) == 55
    assert snapshot['manifest']['quality']['unassigned_centres'] == 0
    assert all(z['population_year'] == 2020 for z in snapshot['demand_zones'])
    assert all(z['location_method'] == 'polygon_representative_point' for z in snapshot['demand_zones'])
    population_rows = json.loads((RAW / 'population2020.json').read_text())['result']['records']
    # Rounded population sums differ from the national total. Preserve observations, never rescale.
    observed = sum(ingest._population(r['Total_Total']) for r in population_rows
                   if r['Number'] != 'Total' and not r['Number'].replace(' ', '').endswith('-Total'))
    assert sum(z['residents'] for z in snapshot['demand_zones']) == observed
    assert snapshot['food_waste'][-1] == {'year': 2025, 'generated_tonnes': 790000,
                                         'recycled_tonnes': 140000, 'disposed_tonnes': 649000,
                                         'recycling_rate_percent': 18}


def test_unknown_invalid_and_staggered_dates_are_quarantined(source_row):
    row = copy.deepcopy(source_row)
    row.update(q1_cleaningstartdate='TBC', q2_cleaningstartdate='31/2/2026',
               q3_cleaningstartdate='10/9/2026', q3_cleaningenddate='7/9/2026',
               remarks_q4='Blk 79 closed on 7/12/2026, Blk 79A closed on 8/12/2026.')
    closures, quarantine = ingest.normalize_closures([row])
    assert not closures
    assert len(quarantine) == 4
    assert quarantine[-1]['reason'] == 'partial_block_closure_needs_operator_review'
    assert quarantine[0]['source_start'] == 'TBC'


def test_both_blocks_fully_closed_preserves_inclusive_dates(source_row):
    row = copy.deepcopy(source_row)
    row['remarks_q1'] = 'Both closed from 30 March to 31 March 2026'
    closures, _ = ingest.normalize_closures([row])
    event = next(c for c in closures if c['id'].endswith('q1'))
    assert (event['start_date'], event['end_date']) == ('2026-03-30', '2026-03-31')


def test_missing_population_is_not_accepted_as_zero():
    assert ingest._population('-') == 0  # Explicit SingStat nil-or-negligible notation.
    for value in ['', None, 'NA', 'TBC', -2]:
        with pytest.raises(ingest.DataQualityError):
            ingest._population(value)


def test_changed_raw_bytes_fail_checksum_before_normalization(tmp_path):
    import shutil
    shutil.copytree(RAW, tmp_path / 'raw')
    path = tmp_path / 'raw' / 'closures.json'
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ingest.DataQualityError, match='Checksum mismatch'):
        ingest.build_snapshot(tmp_path / 'raw')


def test_refresh_failure_preserves_last_good_snapshot_and_removes_stage(tmp_path, monkeypatch):
    path = tmp_path / 'processed' / 'snapshot.json'
    original = b'{"manifest":{"sources":[]},"last_good":true}\n'
    path.parent.mkdir()
    path.write_bytes(original)

    def broken(_):
        raise TimeoutError('simulated network outage')

    monkeypatch.setattr(ingest, 'fetch_tabular', broken)
    with pytest.raises(TimeoutError):
        ingest.refresh(tmp_path)
    assert path.read_bytes() == original
    assert list((tmp_path / 'raw').iterdir()) == []


def test_pagination_collects_all_rows_and_rejects_source_count_changes(monkeypatch):
    responses = [
        {'success': True, 'result': {'total': 2, 'records': [{'_id': 1}], 'fields': []}},
        {'success': True, 'result': {'total': 2, 'records': [{'_id': 2}], 'fields': []}},
    ]
    monkeypatch.setattr(ingest, 'download', lambda _: json.dumps(responses.pop(0)).encode())
    data, _ = ingest.fetch_tabular('dataset-test')
    assert len(json.loads(data)['result']['records']) == 2
    responses.extend([
        {'success': True, 'result': {'total': 2, 'records': [{'_id': 1}], 'fields': []}},
        {'success': True, 'result': {'total': 3, 'records': [{'_id': 2}], 'fields': []}},
    ])
    with pytest.raises(ingest.DataQualityError, match='changed during pagination'):
        ingest.fetch_tabular('dataset-test')


def test_atomic_write_failure_keeps_previous_file(tmp_path, monkeypatch):
    path = tmp_path / 'snapshot.json'
    path.write_text('old')

    def broken_replace(*_):
        raise OSError('simulated filesystem error')

    monkeypatch.setattr(ingest.os, 'replace', broken_replace)
    with pytest.raises(OSError):
        ingest.atomic_json(path, {'new': 'value'})
    assert path.read_text() == 'old'
    assert list(tmp_path.iterdir()) == [path]
