"""Auditable Singapore open-data ingestion and deterministic normalization.

The released snapshot is a real-data baseline, not a simulated population. Geographic
representative points are explicit proxies, and unresolved dates are quarantined.
A failed refresh never replaces the last validated processed snapshot.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shapely.geometry import Point, mapping, shape
from shapely.validation import make_valid

DATASET_IDS = {
    'closures': 'd_bda4baa634dd1cc7a6c7cad5f19e2d68',
    'population2020': 'd_d95ae740c0f8961a0b10435836660ce0',
    'planning_areas': 'd_4765db0e87b9c86336792efe8a1f7a66',
    'subzones': 'd_8594ae9ff96d0c708bc2af633048edfb',
    'waste': 'd_daf568968ab40dc81e7b08887a83c8fa',
}
SOURCE_METADATA = {
    'closures': {'title': 'Dates of Hawker Centres Closure', 'agency': 'NEA',
                 'observation_period': '2026 schedule; selected earlier works retained'},
    'population2020': {'title': 'Resident Population by Planning Area/Subzone, Age and Sex (Census 2020)',
                       'agency': 'SingStat', 'observation_period': 'Census of Population 2020'},
    'planning_areas': {'title': 'Master Plan 2019 Planning Area Boundary (No Sea)',
                       'agency': 'URA', 'observation_period': 'Master Plan 2019'},
    'subzones': {'title': 'Master Plan 2019 Subzone Boundary (No Sea)',
                 'agency': 'URA', 'observation_period': 'Master Plan 2019'},
    'waste': {'title': 'Waste Management and Overall Recycling Rates, Annual',
              'agency': 'SingStat / NEA', 'observation_period': '2000–2025'},
}
FILENAMES = {key: key + ('.geojson' if key in {'planning_areas', 'subzones'} else '.json')
             for key in DATASET_IDS}
LICENSE_URL = 'https://data.gov.sg/open-data-licence'
MIRRORS = {
    'planning_areas': 'https://drive.google.com/uc?export=download&id=1kwvpiabQyc49CErAP5cTXarO7x5sWTeX',
    'subzones': 'https://raw.githubusercontent.com/ethan-cyj/Public-Transportation-In-Singapore/660517a4afe692938477d8326efa8f20bd71f88d/data/SP1/MasterPlan2019SubzoneBoundaryNoSeaGEOJSON.geojson',
}
SENIOR_COLUMNS = ['Total_65_69', 'Total_70_74', 'Total_75_79', 'Total_80_84',
                  'Total_85_89', 'Total_90andOver']


class DataQualityError(ValueError):
    """Source data does not meet the published contract; do not publish it."""


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace('+00:00', 'Z')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()


def atomic_json(path: Path, value: Any) -> None:
    """Replace a JSON file only once all bytes are written and flushed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(_json_bytes(value))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def download(url: str, *, timeout: float = 25, attempts: int = 3) -> bytes:
    """Bounded HTTPS download; retry transient failures, not authentication errors."""
    if not url.startswith('https://'):
        raise ValueError('Only HTTPS source URLs are allowed')
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'HawkerBridge/1.0 (open-data research)',
                                                           'Accept': 'application/json,*/*;q=0.8'})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = response.read(25_000_001)
            if len(data) > 25_000_000:
                raise DataQualityError('Source exceeds 25 MB size limit')
            return data
        except (urllib.error.URLError, TimeoutError) as exc:
            if isinstance(exc, urllib.error.HTTPError) and exc.code not in {408, 429, 500, 502, 503, 504}:
                raise
            if attempt == attempts - 1:
                raise
            time.sleep(min(2 ** attempt, 4))
    raise RuntimeError('Unreachable')


def fetch_tabular(dataset_id: str) -> tuple[bytes, str]:
    """Use the documented public datastore endpoint, respecting pagination."""
    base = 'https://data.gov.sg/api/action/datastore_search'
    records: list[dict] = []
    fields: list[dict] = []
    total = None
    for _ in range(100):
        query = urllib.parse.urlencode({'resource_id': dataset_id, 'limit': 1000, 'offset': len(records)})
        payload = json.loads(download(base + '?' + query))
        result = payload.get('result', {})
        if payload.get('success') is not True or not isinstance(result.get('records'), list):
            raise DataQualityError(f'Invalid datastore response for {dataset_id}')
        expected = int(result['total'])
        if total is not None and expected != total:
            raise DataQualityError('Source changed during pagination; retry the entire refresh')
        total = expected
        fields = result.get('fields', fields)
        page = result['records']
        records.extend(page)
        if len(records) == total:
            result = {'resource_id': dataset_id, 'fields': fields, 'records': records, 'total': total}
            return _json_bytes({'success': True, 'result': result}), base + '?resource_id=' + dataset_id
        if not page or len(records) > total:
            raise DataQualityError('Incomplete or inconsistent pagination')
    raise DataQualityError('Pagination limit exceeded')


def fetch_geometry(key: str, *, allow_mirror: bool = False) -> tuple[bytes, str, bool]:
    endpoint = f'https://api-open.data.gov.sg/v1/public/api/datasets/{DATASET_IDS[key]}/poll-download'
    try:
        result = json.loads(download(endpoint))
        url = result.get('data', {}).get('url')
        if result.get('code') != 0 or not url:
            raise DataQualityError(f'Geometry download unavailable: {key}')
        return download(url), endpoint, False
    except (urllib.error.URLError, TimeoutError, DataQualityError):
        if not allow_mirror:
            raise
        # Deliberate explicit opt-in, with original source and transport mirror both recorded.
        return download(MIRRORS[key]), MIRRORS[key], True


def _records(path: Path) -> list[dict]:
    value = json.loads(path.read_bytes())
    if value.get('success') is not True:
        raise DataQualityError(f'Invalid source payload: {path.name}')
    rows = value['result']['records']
    if len(rows) != int(value['result']['total']):
        raise DataQualityError(f'Truncated source payload: {path.name}')
    return rows


def _name(value: str) -> str:
    return re.sub(r'[^A-Z0-9]', '', value.upper())


def _attributes(feature: dict) -> dict:
    props = dict(feature['properties'])
    # Older official URA exports encode their attributes in a KML HTML table.
    if 'Description' in props:
        for key, value in re.findall(r'<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>',
                                     props['Description'], flags=re.I | re.S):
            props[html.unescape(re.sub('<[^>]+>', '', key)).strip()] = html.unescape(
                re.sub('<[^>]+>', '', value)).strip()
    return props


def _features(path: Path) -> list[tuple[dict, Any]]:
    value = json.loads(path.read_bytes())
    if value.get('type') != 'FeatureCollection' or not value.get('features'):
        raise DataQualityError(f'Invalid geometry: {path.name}')
    features = []
    for feature in value['features']:
        geom = shape(feature['geometry'])
        if not geom.is_valid:
            geom = make_valid(geom)
        if geom.is_empty or geom.geom_type not in {'Polygon', 'MultiPolygon'}:
            raise DataQualityError('Geometry must be a non-empty polygon')
        features.append((_attributes(feature), geom))
    return features


def parse_source_date(value: Any) -> str | None:
    text = str(value or '').strip()
    if text.upper() in {'', 'NA', 'N.A.', 'NIL', 'TBC', 'TBA', '-', 'NULL'}:
        return None
    try:
        return datetime.strptime(text, '%d/%m/%Y').date().isoformat()
    except ValueError:
        return None


def _population(value: Any) -> int:
    # SingStat explicitly defines '-' as nil or negligible, rather than an unknown count.
    text = str(value).strip().replace(',', '')
    if text == '-':
        return 0
    if not text.isdigit():
        raise DataQualityError(f'Unrecognized population token: {value!r}')
    return int(text)


def normalize_closures(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    closures, quarantine = [], []
    for row in rows:
        centre_id = f"hc-{int(row['serial_no']):03d}"
        entries = [(f'q{q}', f'q{q}_cleaningstartdate', f'q{q}_cleaningenddate',
                    f'remarks_q{q}', 'cleaning') for q in range(1, 5)]
        entries.append(('works', 'other_works_startdate', 'other_works_enddate', 'remarks_other_works', 'works'))
        for key, start_col, end_col, remarks_col, kind in entries:
            start, end = parse_source_date(row[start_col]), parse_source_date(row[end_col])
            remarks = str(row.get(remarks_col, '')).strip()
            base = {'id': f'{centre_id}-{key}', 'centre_id': centre_id, 'kind': kind,
                    'source_start': row[start_col], 'source_end': row[end_col], 'source_text': remarks}
            if kind == 'works' and all(str(row[col]).strip().upper() in {'NA', '', 'NIL'} for col in [start_col, end_col]):
                continue  # Source explicitly records no other works.
            if start is None or end is None or end < start:
                quarantine.append({**base, 'reason': 'unresolved_or_invalid_date'})
                continue
            # A centre-level row sometimes aggregates two blocks with staggered closures.
            # Without block-level capacity there is no defensible full-centre shutdown label.
            if 'blk' in remarks.lower() and 'closed' in remarks.lower() and 'both closed' not in remarks.lower():
                quarantine.append({**base, 'reason': 'partial_block_closure_needs_operator_review'})
                continue
            closures.append({**base, 'start_date': start, 'end_date': end})
    return sorted(closures, key=lambda x: (x['start_date'], x['id'])), quarantine


def normalize_food_waste(rows: list[dict]) -> list[dict]:
    series: dict[int, dict] = {}
    section = None
    sections = {'Total Generated': 'generated_tonnes', 'Total Recycled': 'recycled_tonnes',
                'Total Disposed': 'disposed_tonnes', 'Recycling Rate': 'recycling_rate_percent'}
    for row in rows:
        label = str(row['DataSeries']).strip()
        if label in sections:
            section = sections[label]
        elif label == 'Food' and section:
            for year, value in row.items():
                if year.isdigit() and re.fullmatch(r'\d+', str(value)):
                    series.setdefault(int(year), {'year': int(year)})[section] = int(value)
    if not series or not all(len(row) == 5 for row in series.values()):
        raise DataQualityError('Food-waste time series is missing required sections')
    return [series[year] for year in sorted(series)]


def build_snapshot(raw_dir: str | Path) -> dict:
    raw_dir = Path(raw_dir)
    provenance = json.loads((raw_dir / 'provenance.json').read_bytes())
    for source in provenance['sources']:
        actual = digest((raw_dir / source['filename']).read_bytes())
        if actual != source['sha256']:
            raise DataQualityError(f"Checksum mismatch: {source['filename']}")
    rows = _records(raw_dir / FILENAMES['closures'])
    areas = _features(raw_dir / FILENAMES['planning_areas'])
    subzones = _features(raw_dir / FILENAMES['subzones'])
    if len(areas) != 55 or len(subzones) != 332:
        raise DataQualityError('Unexpected Master Plan 2019 boundary coverage')
    area_shapes = [(str(props['PLN_AREA_N']).title(), geom) for props, geom in areas]
    centres = []
    spatial_review = []
    for row in rows:
        lat, lng = float(row['latitude_hc']), float(row['longitude_hc'])
        if not (1.1 < lat < 1.5 and 103.5 < lng < 104.1):
            raise DataQualityError(f"Invalid Singapore centre coordinate: {row['name']}")
        point = Point(lng, lat)
        matches = [name for name, geom in area_shapes if geom.covers(point)]
        if len(matches) != 1:
            # Do not silently shift a centre across a planning boundary.
            spatial_review.append({'centre_id': f"hc-{int(row['serial_no']):03d}", 'matches': matches})
        food, market = int(row['no_of_food_stalls']), int(row['no_of_market_stalls'])
        if min(food, market) < 0:
            raise DataQualityError('Negative stall count')
        centres.append({'id': f"hc-{int(row['serial_no']):03d}", 'name': row['name'],
                        'lat': lat, 'lng': lng, 'address': row['address_myenv'],
                        'planning_area': matches[0] if len(matches) == 1 else 'Unassigned',
                        'food_stalls': food, 'market_stalls': market, 'status': row['status']})
    closures, quarantine = normalize_closures(rows)
    zone_lookup = {(_name(p['PLN_AREA_N']), _name(p['SUBZONE_N'])): (p, geom) for p, geom in subzones}
    zones, population_totals = [], []
    current_area = None
    for row in _records(raw_dir / FILENAMES['population2020']):
        name = row['Number'].strip()
        if name == 'Total':
            continue
        values = {'residents': _population(row['Total_Total']),
                  'seniors': sum(_population(row[c]) for c in SENIOR_COLUMNS)}
        if re.search(r'\s*-\s*Total$', name):
            current_area = re.sub(r'\s*-\s*Total$', '', name).strip()
            population_totals.append({'planning_area': current_area, **values})
            continue
        key = (_name(current_area or ''), _name(name))
        if key not in zone_lookup:
            raise DataQualityError(f'Unmatched census geography: {current_area}/{name}')
        props, geom = zone_lookup[key]
        point = geom.representative_point()
        zones.append({'id': props['SUBZONE_C'].lower(), 'name': name, 'planning_area': current_area,
                      'lat': round(point.y, 7), 'lng': round(point.x, 7), **values,
                      'location_method': 'polygon_representative_point', 'population_year': 2020,
                      'geometry': mapping(geom.simplify(0.00004, preserve_topology=True))})
    boundary_features = []
    for props, geom in areas:
        name = str(props['PLN_AREA_N']).title()
        total = next((row for row in population_totals if _name(row['planning_area']) == _name(name)), None)
        if total is None:
            raise DataQualityError(f'Unmatched planning area: {name}')
        boundary_features.append({'type': 'Feature', 'geometry': mapping(geom.simplify(0.00004, preserve_topology=True)),
                                  'properties': {'name': name, 'planning_area': name, 'id': props['PLN_AREA_C'],
                                                 'residents': total['residents'], 'seniors': total['seniors']}})
    limitations = [
        'Resident and senior counts are Census 2020 observations, not 2026 population estimates; published counts are rounded.',
        'Subzone locations are polygon representative points, not homes or population-weighted centroids. Distance is a spatial screening proxy.',
        'NEA stall counts measure infrastructure, not operating stalls, spare meal capacity, demand or observed footfall.',
        'Missing/TBC and staggered block closure intervals are quarantined, so scheduled-open means no resolved full-centre closure recorded, not a guarantee.',
        'The closure calendar is a current 2026 schedule with some older works retained; it is not a complete historical closure archive and has no reliable permanent-closure labels.',
        'Food-waste data are annual national totals covering all sectors. No centre-level waste or causal intervention outcome is observed.',
        'URA boundaries are from Master Plan 2019; geometry is simplified only for display and is not a pedestrian routing network.',
        'Only NEA-listed hawker centres are included; coffee shops, food courts and other meal providers are omitted.',
    ]
    if any(source.get('mirror') for source in provenance['sources']):
        limitations.append('Some archived URA geometry was retrieved from attributed public mirrors because the official download endpoint returned HTTP 403; raw checksums and transport URLs are recorded.')
    manifest = {'schema_version': 1, 'fetched_at': provenance['fetched_at'], 'built_at': utc_now(),
                'dataset_count': len(provenance['sources']), 'population_year': 2020,
                'closures_year': Counter(int(c['start_date'][:4]) for c in closures if c['kind'] == 'cleaning').most_common(1)[0][0], 'sources': provenance['sources'], 'limitations': limitations,
                'quality': {'centres': len(centres), 'resolved_closure_intervals': len(closures),
                            'quarantined_closure_intervals': len(quarantine), 'demand_zones': len(zones),
                            'populated_demand_zones': sum(z['residents'] > 0 for z in zones),
                            'planning_areas': len(areas), 'unassigned_centres': len(spatial_review),
                            'population_join_coverage_percent': 100.0,
                            'resident_sum_subzones': sum(z['residents'] for z in zones),
                            'senior_sum_subzones': sum(z['seniors'] for z in zones)}}
    snapshot = {'centres': centres, 'closures': closures, 'demand_zones': zones,
                'planning_area_population': population_totals,
                'boundaries': {'type': 'FeatureCollection', 'features': boundary_features},
                'food_waste': normalize_food_waste(_records(raw_dir / FILENAMES['waste'])),
                'quarantine': quarantine, 'spatial_review': spatial_review, 'manifest': manifest}
    validate_snapshot(snapshot)
    manifest['content_sha256'] = digest(_json_bytes({key: value for key, value in snapshot.items() if key != 'manifest'}))
    return snapshot


def validate_snapshot(snapshot: dict) -> None:
    for key in ['centres', 'closures', 'demand_zones']:
        ids = [row['id'] for row in snapshot[key]]
        if len(ids) != len(set(ids)):
            raise DataQualityError(f'Duplicate IDs in {key}')
    if len(snapshot['centres']) < 100 or len(snapshot['demand_zones']) != 332:
        raise DataQualityError('Incomplete national coverage')
    ids = {c['id'] for c in snapshot['centres']}
    for closure in snapshot['closures']:
        if closure['centre_id'] not in ids or closure['start_date'] > closure['end_date']:
            raise DataQualityError('Invalid closure relationship or dates')
    for zone in snapshot['demand_zones']:
        if not 0 <= zone['seniors'] <= zone['residents'] + 30:
            raise DataQualityError('Inconsistent rounded population counts')
    if snapshot['manifest']['quality']['unassigned_centres']:
        raise DataQualityError('Centres outside known planning areas require review')
    _json_bytes(snapshot)  # rejects NaN and infinity


def refresh(data_dir: str | Path, *, allow_mirror: bool = False, reuse_geometry: bool = True) -> dict:
    """Acquire, validate, then atomically publish. Last-good snapshot survives errors.

    Slow-changing geometry may be reused from the prior raw bundle after checksum
    verification, retaining its original retrieval timestamp and mirror status.
    """
    data_dir = Path(data_dir)
    raw_root = data_dir / 'raw'
    raw_root.mkdir(parents=True, exist_ok=True)
    snapshot_path = data_dir / 'processed' / 'snapshot.json'
    previous = json.loads(snapshot_path.read_bytes()) if snapshot_path.exists() else None
    stage = Path(tempfile.mkdtemp(prefix='.refresh-', dir=raw_root))
    fetched_at = utc_now()
    sources = []
    try:
        for key, dataset_id in DATASET_IDS.items():
            reused = None
            if key in MIRRORS and reuse_geometry and previous:
                reused = next((s for s in previous['manifest']['sources'] if s['key'] == key), None)
            if reused:
                old_path = data_dir / reused['raw_path']
                content = old_path.read_bytes()
                if digest(content) != reused['sha256']:
                    raise DataQualityError('Cached geometry checksum mismatch')
                source = dict(reused)
                source['reused_at'] = fetched_at
            else:
                if key in MIRRORS:
                    content, transport, mirror = fetch_geometry(key, allow_mirror=allow_mirror)
                else:
                    content, transport = fetch_tabular(dataset_id)
                    mirror = False
                source = {'key': key, 'dataset_id': dataset_id, 'filename': FILENAMES[key],
                          'url': f'https://data.gov.sg/datasets/{dataset_id}/view',
                          'transport_url': transport, 'mirror': mirror, 'fetched_at': fetched_at,
                          'license': 'Singapore Open Data Licence', 'license_url': LICENSE_URL,
                          'sha256': digest(content), 'bytes': len(content)}
            source.update(SOURCE_METADATA[key])
            (stage / FILENAMES[key]).write_bytes(content)
            sources.append(source)
        run_id = datetime.now(UTC).strftime('%Y%m%dT%H%M%S') + '-' + os.urandom(3).hex()
        for source in sources:
            source['raw_path'] = f'raw/{run_id}/{source["filename"]}'
        atomic_json(stage / 'provenance.json', {'fetched_at': fetched_at, 'sources': sources})
        snapshot = build_snapshot(stage)
        stage.rename(raw_root / run_id)
        atomic_json(snapshot_path, snapshot)
        return snapshot
    finally:
        if stage.exists():
            shutil.rmtree(stage)
