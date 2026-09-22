"""Idempotent retention worker; run hourly with managed service credentials.

`python -m hawkerbridge.firebase_cleanup --execute --limit 1000` deletes expired
guest workspaces and resumes account deletions. Without --execute, only counts
eligible workspaces. The Spark database has no paid TTL dependency.
"""

from __future__ import annotations

import argparse
import json
import logging

from .config import Settings
from .firebase_identity import FirebaseIdentity
from .firestore_store import FirestoreStore


def cleanup(store, identity, *, execute=False, limit=100) -> dict:
    if not 1 <= limit <= 1000:
        raise ValueError("Cleanup limit must be between 1 and 1000")
    owners = store.cleanup_candidates(limit)
    result = dict(
        eligible_workspaces=len(owners),
        deleted_workspaces=0,
        failures=0,
        expired_limit_records=0,
        dry_run=not execute,
    )
    if not execute:
        return result
    for owner in owners:
        try:
            store.begin_deletion(owner)
            identity.disable_user(owner)
            store.delete_user_plans(owner)
            identity.delete_user(owner)
            store.finish_deletion(owner)
            result["deleted_workspaces"] += 1
        except Exception as error:
            # Tombstone persists; next invocation can resume safely. Never log PII.
            logging.getLogger("hawkerbridge").warning(
                "Retention cleanup failed: %s", type(error).__name__
            )
            result["failures"] += 1
    result["expired_limit_records"] = store.cleanup_expired_limits()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    settings = Settings()
    settings.validate()
    if settings.auth_mode != "firebase":
        parser.error("The retention worker requires Firebase/Firestore mode")
    identity = FirebaseIdentity(settings)
    try:
        result = cleanup(
            FirestoreStore(settings, app=identity.app),
            identity,
            execute=args.execute,
            limit=args.limit,
        )
        print(json.dumps(result, sort_keys=True))
        return 1 if result["failures"] else 0
    finally:
        identity.close()


if __name__ == "__main__":
    raise SystemExit(main())
