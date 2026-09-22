#!/usr/bin/env python3
"""Refresh live sources atomically, or rebuild the exact checked-in raw baseline."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from hawkerbridge.ingest import atomic_json, build_snapshot, refresh  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'data')
    parser.add_argument('--rebuild', type=Path, help='Rebuild from a raw directory; makes no network calls')
    parser.add_argument('--allow-mirror', action='store_true', help='Explicitly allow attributed archived URA mirrors')
    parser.add_argument('--refresh-geometry', action='store_true', help='Fetch boundaries instead of reusing checksummed static geometry')
    args = parser.parse_args()
    try:
        if args.rebuild:
            snapshot = build_snapshot(args.rebuild)
            atomic_json(args.data_dir / 'processed' / 'snapshot.json', snapshot)
        else:
            snapshot = refresh(args.data_dir, allow_mirror=args.allow_mirror, reuse_geometry=not args.refresh_geometry)
    except Exception as exc:
        print(f'Refresh failed; previous processed snapshot retained: {exc}', file=sys.stderr)
        return 1
    print(json.dumps(snapshot['manifest']['quality'], indent=2))
    print(f"Verified snapshot: {snapshot['manifest']['content_sha256']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
