"""Inspect fetched source snapshots without pretending missing values are observations."""
import collections
import datetime as dt
import json
from pathlib import Path

root = Path(__file__).parent
rows = json.loads((root / 'closure-old.json').read_text())['result']['records']
dates = []
unknown = []
for row in rows:
    for quarter in range(1, 5):
        a, b = row[f'q{quarter}_cleaningstartdate'], row[f'q{quarter}_cleaningenddate']
        try:
            start, end = [dt.datetime.strptime(value, '%d/%m/%Y').date() for value in (a, b)]
            dates.append((row['name'], start, end))
        except ValueError:
            unknown.append((row['name'], quarter, a, b))
print(json.dumps({'centres': len(rows), 'food_stalls': sum(int(r['no_of_food_stalls']) for r in rows),
    'cleaning_intervals': len(dates), 'unknown_cleaning': unknown,
    'status_counts': dict(collections.Counter(r['status'] for r in rows))}, indent=2))
