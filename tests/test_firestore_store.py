from __future__ import annotations

import gzip
import hashlib
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta

import pytest
from hawkerbridge.firebase_cleanup import cleanup
from hawkerbridge.firestore_store import (
    MAX_JSON_BYTES,
    FirestoreStore,
    FirestoreStoreError,
    InactiveWorkspaceError,
    PlanQuotaError,
    decode_payload,
    encode_payload,
)
from support_firebase import Clock, MemoryFirestore, example_plan, firebase_settings, transactional


@pytest.fixture
def storage(monkeypatch):
    monkeypatch.setattr(
        "hawkerbridge.firestore_store.google_firestore.transactional", transactional
    )
    client, clock = MemoryFirestore(), Clock()
    return FirestoreStore(
        firebase_settings(plan_limit=3, guest_plan_limit=2), client=client, clock=clock
    )


def user(storage, identifier="owner", mode="firebase"):
    storage.ensure_user({"id": identifier, "mode": mode})
    return identifier


def test_owner_isolation_metadata_projection_and_immutable_results(storage):
    a, b = user(storage), user(storage, "other")
    plan = example_plan()
    storage.save_plan(a, plan)
    assert storage.get_plan(b, plan["id"]) is None
    assert storage.list_plans(b) == []
    listed = storage.list_plans(a)
    assert listed[0]["result"] == {"summary": plan["result"]["summary"]}
    assert "source_manifest" not in listed[0]
    assert storage.client.projections == [("metadata", "summary"), ("metadata", "summary")]
    assert storage.get_plan(a, plan["id"]) == plan
    edited = deepcopy(plan)
    edited.update(title="Reviewed proposal", status="reviewed", reviewed_by="Shivam")
    storage.update_plan(a, edited, plan["updated_at"])
    assert storage.get_plan(a, plan["id"]) == edited
    edited["result"]["summary"]["allocated_meals"] = 999
    with pytest.raises(PlanQuotaError, match="immutable"):
        storage.update_plan(a, edited, plan["updated_at"])
    assert storage.get_plan(a, plan["id"])["result"]["summary"]["allocated_meals"] == 225
    assert storage._user(a).get().to_dict()["plan_count"] == 1


def test_concurrent_create_limit_is_atomic_and_delete_frees_slot(storage):
    owner = user(storage, mode="guest")

    def attempt(i):
        try:
            storage.save_plan(owner, example_plan(f"p-{i}"))
            return True
        except PlanQuotaError:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(attempt, range(20))) == 2
    plans = storage.list_plans(owner)
    assert len(plans) == storage._user(owner).get().to_dict()["plan_count"] == 2
    assert storage.delete_plan(owner, plans[0]["id"])
    assert not storage.delete_plan(owner, plans[0]["id"])
    assert attempt(30)
    assert storage._user(owner).get().to_dict()["plan_count"] == 2


def test_guest_expiry_and_deletion_tombstone_prevent_new_writes(storage):
    owner = user(storage, mode="guest")
    storage.save_plan(owner, example_plan())
    storage.clock.now += timedelta(days=7)
    assert not storage.user_active(owner)
    with pytest.raises(InactiveWorkspaceError):
        storage.ensure_user({"id": owner, "mode": "guest"})
    with pytest.raises(InactiveWorkspaceError):
        storage.save_plan(owner, example_plan("later"))
    assert storage.cleanup_candidates() == [owner]
    other = user(storage, "other")
    storage.begin_deletion(other)
    assert not storage.user_active(other)
    with pytest.raises(InactiveWorkspaceError):
        storage.save_plan(other, example_plan())
    assert set(storage.cleanup_candidates()) == {owner, other}


def test_distributed_limits_and_per_cookie_logout_revocation(storage):
    with ThreadPoolExecutor(max_workers=8) as pool:
        granted = list(pool.map(lambda _: storage.rate_allowed("shared-bucket", 5, 60), range(20)))
    assert sum(granted) == 5
    storage.clock.now += timedelta(seconds=61)
    assert storage.rate_allowed("shared-bucket", 5, 60)
    assert not storage.session_revoked("opaque-cookie")
    storage.revoke_session("opaque-cookie", (storage.clock.now + timedelta(minutes=1)).timestamp())
    assert storage.session_revoked("opaque-cookie")
    assert not storage.session_revoked("different-cookie")
    assert "opaque-cookie" not in str(storage.client.docs)
    storage.clock.now += timedelta(hours=2)
    assert not storage.session_revoked("opaque-cookie")
    assert storage.cleanup_expired_limits() == 2


def test_payload_size_corruption_and_decompression_bomb_are_rejected():
    payload, digest = encode_payload(example_plan())
    assert decode_payload(payload, digest)["id"] == "plan-one"
    for malformed in (payload[:-1], payload + b"trailing", b"not-gzip"):
        with pytest.raises(FirestoreStoreError):
            decode_payload(malformed, digest)
    with pytest.raises(FirestoreStoreError):
        decode_payload(payload, "0" * 64)
    bomb = b"a" * (MAX_JSON_BYTES + 1)
    with pytest.raises(FirestoreStoreError):
        decode_payload(gzip.compress(bomb), hashlib.sha256(bomb).hexdigest())
    huge = example_plan()
    huge["result"]["geometry"] = "x" * MAX_JSON_BYTES
    with pytest.raises(PlanQuotaError):
        encode_payload(huge)


def test_metadata_tampering_and_invalid_identifiers_fail_closed(storage):
    owner = user(storage)
    storage.save_plan(owner, example_plan())
    ref = storage._user(owner).collection("plans").document("plan-one")
    data = ref.get().to_dict()
    data["metadata"]["parameters"]["budget"] = 999
    ref.set(data)
    with pytest.raises(FirestoreStoreError, match="inconsistent"):
        storage.get_plan(owner, "plan-one")
    for identifier in ("../other", "", "x" * 129, "a/b"):
        with pytest.raises(ValueError):
            storage.get_plan(owner, identifier)


def test_cleanup_retries_partial_failure_and_dry_run_is_read_only(storage):
    owner = user(storage, mode="guest")
    storage.save_plan(owner, example_plan())
    storage.clock.now += timedelta(days=8)

    class Identity:
        fail = True
        deleted = []

        def disable_user(self, uid):
            pass

        def delete_user(self, uid):
            if self.fail:
                raise RuntimeError("Transient provider failure")
            self.deleted.append(uid)

    identity = Identity()
    before = deepcopy(storage.client.docs)
    assert cleanup(storage, identity)["eligible_workspaces"] == 1
    assert storage.client.docs == before
    failed = cleanup(storage, identity, execute=True)
    assert failed["failures"] == 1
    assert not storage.user_active(owner)
    assert storage.list_plans(owner) == []
    assert storage._user(owner).get().to_dict()["deleting"]
    identity.fail = False
    assert cleanup(storage, identity, execute=True)["deleted_workspaces"] == 1
    assert identity.deleted == [owner]
    assert not storage._user(owner).get().exists
    assert cleanup(storage, identity, execute=True)["eligible_workspaces"] == 0


def test_update_transaction_rejects_stale_revision_and_never_resurrects_delete(storage):
    from hawkerbridge.plan_errors import PlanConflictError, PlanNotFoundError

    owner = user(storage)
    original = example_plan()
    storage.save_plan(owner, original)
    first, stale = deepcopy(original), deepcopy(original)
    first.update(notes="New notes", updated_at="2026-09-22T12:01:00+00:00")
    storage.update_plan(owner, first, original["updated_at"])
    stale.update(status="reviewed", updated_at="2026-09-22T12:02:00+00:00")
    with pytest.raises(PlanConflictError):
        storage.update_plan(owner, stale, original["updated_at"])
    assert storage.get_plan(owner, original["id"])["notes"] == "New notes"
    assert storage.get_plan(owner, original["id"])["status"] == "draft"
    storage.delete_plan(owner, original["id"])
    with pytest.raises(PlanNotFoundError):
        storage.update_plan(owner, first, first["updated_at"])
    assert storage.list_plans(owner) == []
    assert storage._user(owner).get().to_dict()["plan_count"] == 0
