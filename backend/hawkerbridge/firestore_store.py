"""Durable, owner-scoped plans and distributed limits for public hosting.

The application service account is the only database client. Public Firestore
rules must deny direct browser access. Calculation payloads are immutable gzip
JSON, with a conservative document-size guard and bounded decompression.
"""

from __future__ import annotations

import gzip
import hashlib
import hmac
import json
import zlib
from datetime import UTC, datetime, timedelta

from firebase_admin import firestore
from google.cloud import firestore as google_firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from .firebase_identity import firebase_app
from .plan_errors import PlanConflictError, PlanNotFoundError

MAX_JSON_BYTES = 3 * 1024 * 1024
MAX_PAYLOAD_BYTES = 800 * 1024
MAX_METADATA_BYTES = 32 * 1024
_RPC = {"timeout": 6, "retry": None}
_IMMUTABLE = (
    "id",
    "date",
    "created_at",
    "parameters",
    "result",
    "source_manifest",
    "engine_code_sha256",
)
_META = (
    "id",
    "title",
    "status",
    "date",
    "created_at",
    "updated_at",
    "parameters",
    "notes",
    "reviewed_at",
    "reviewed_by",
)


class FirestoreStoreError(RuntimeError):
    status_code = 503


class PlanQuotaError(FirestoreStoreError):
    status_code = 409


class InactiveWorkspaceError(FirestoreStoreError):
    status_code = 401


def owner_key(owner: str) -> str:
    if not isinstance(owner, str) or not 1 <= len(owner) <= 128:
        raise ValueError("A valid owner identity is required")
    return hashlib.sha256(owner.encode()).hexdigest()


def plan_key(plan_id: str) -> str:
    if (
        not isinstance(plan_id, str)
        or not 1 <= len(plan_id) <= 128
        or any(
            c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
            for c in plan_id
        )
    ):
        raise ValueError("A valid plan identifier is required")
    return plan_id


def encode_payload(plan: dict) -> tuple[bytes, str]:
    raw = json.dumps(
        {k: plan[k] for k in _IMMUTABLE if k in plan},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()
    if len(raw) > MAX_JSON_BYTES:
        raise PlanQuotaError("This proposal exceeds the safe storage size.")
    compressed = gzip.compress(raw, compresslevel=6, mtime=0)
    if len(compressed) > MAX_PAYLOAD_BYTES:
        raise PlanQuotaError("This proposal exceeds the safe storage size.")
    return compressed, hashlib.sha256(raw).hexdigest()


def decode_payload(blob: bytes, expected_hash: str) -> dict:
    if not isinstance(blob, bytes) or len(blob) > MAX_PAYLOAD_BYTES:
        raise FirestoreStoreError("Stored proposal is invalid.")
    try:
        decoder = zlib.decompressobj(wbits=31)
        raw = decoder.decompress(blob, MAX_JSON_BYTES + 1)
        if (
            len(raw) > MAX_JSON_BYTES
            or not decoder.eof
            or decoder.unused_data
            or decoder.unconsumed_tail
        ):
            raise ValueError("Invalid compressed payload")
        if not isinstance(expected_hash, str) or not hmac.compare_digest(
            hashlib.sha256(raw).hexdigest(), expected_hash
        ):
            raise ValueError("Payload integrity mismatch")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError("Invalid payload object")
        return result
    except (ValueError, zlib.error, UnicodeError) as error:
        raise FirestoreStoreError("Stored proposal failed its integrity check.") from error


class FirestoreStore:
    def __init__(self, settings, *, client=None, app=None, clock=None):
        self.client = client or firestore.client(
            app=app or firebase_app(settings.firebase_project),
            database_id=settings.firestore_database,
        )
        self.clock = clock or (lambda: datetime.now(UTC))
        self.guest_days = settings.guest_retention_days
        self.guest_limit = settings.guest_plan_limit
        self.plan_limit = settings.plan_limit

    def _user(self, owner: str):
        return self.client.collection("hb_users").document(owner_key(owner))

    def _transaction(self, function):
        return google_firestore.transactional(function)(self.client.transaction(max_attempts=3))

    def _active(self, data: dict | None, owner: str) -> bool:
        return bool(
            data
            and data.get("owner_uid") == owner
            and not data.get("deleting")
            and (not data.get("expires_at") or data["expires_at"] > self.clock())
        )

    def ensure_user(self, user: dict):
        ref = self._user(user["id"])

        def operation(tx):
            record = ref.get(transaction=tx, **_RPC)
            if record.exists:
                if not self._active(record.to_dict(), user["id"]):
                    raise InactiveWorkspaceError("This workspace expired or is being deleted.")
                return
            now = self.clock()
            data = dict(
                owner_uid=user["id"],
                mode=user["mode"],
                created_at=now,
                plan_count=0,
                deleting=False,
            )
            if user["mode"] == "guest":
                data["expires_at"] = now + timedelta(days=self.guest_days)
            tx.create(ref, data)

        self._transaction(operation)

    def user_active(self, owner: str) -> bool:
        record = self._user(owner).get(**_RPC)
        return self._active(record.to_dict() if record.exists else None, owner)

    def list_plans(self, owner: str) -> list[dict]:
        query = (
            self._user(owner)
            .collection("plans")
            .select(["metadata", "summary"])
            .limit(self.plan_limit)
        )
        # A projection keeps all embedded geometry out of the list response.
        rows = []
        for record in query.stream(**_RPC):
            doc = record.to_dict()
            rows.append({**doc["metadata"], "result": {"summary": doc["summary"]}})
        return sorted(rows, key=lambda p: (p["updated_at"], p["id"]), reverse=True)

    def get_plan(self, owner: str, plan_id: str) -> dict | None:
        record = self._user(owner).collection("plans").document(plan_key(plan_id)).get(**_RPC)
        if not record.exists:
            return None
        doc = record.to_dict()
        result = decode_payload(doc.get("payload"), doc.get("payload_sha256"))
        metadata = doc.get("metadata", {})
        if result.get("id") != plan_id or any(
            metadata.get(k) != result.get(k) for k in ("id", "date", "created_at", "parameters")
        ):
            raise FirestoreStoreError("Stored proposal metadata is inconsistent.")
        return {**result, **metadata}

    def save_plan(self, owner: str, plan: dict):
        self._write_plan(owner, plan, expected_updated_at=None)

    def update_plan(self, owner: str, plan: dict, expected_updated_at: str):
        if not expected_updated_at:
            raise PlanConflictError()
        self._write_plan(owner, plan, expected_updated_at=expected_updated_at)

    def _write_plan(self, owner: str, plan: dict, *, expected_updated_at: str | None):
        payload, digest = encode_payload(plan)
        metadata = {k: plan[k] for k in _META if k in plan}
        summary = plan["result"]["summary"]
        if (
            len(json.dumps([metadata, summary], ensure_ascii=False, allow_nan=False).encode())
            > MAX_METADATA_BYTES
        ):
            raise PlanQuotaError("This proposal's notes exceed the safe storage size.")
        user_ref = self._user(owner)
        ref = user_ref.collection("plans").document(plan_key(plan["id"]))

        def operation(tx):
            user_record = user_ref.get(transaction=tx, **_RPC)
            current = ref.get(transaction=tx, **_RPC)
            user = user_record.to_dict() if user_record.exists else None
            if not self._active(user, owner):
                raise InactiveWorkspaceError("This workspace expired or is being deleted.")
            if expected_updated_at is not None:
                if not current.exists:
                    raise PlanNotFoundError()
                if current.to_dict().get("metadata", {}).get("updated_at") != expected_updated_at:
                    raise PlanConflictError()
            if current.exists:
                if expected_updated_at is None:
                    raise PlanConflictError()
                if current.to_dict().get("payload_sha256") != digest:
                    raise PlanQuotaError("Saved calculations are immutable. Create a new proposal.")
                tx.update(ref, {"metadata": metadata})
                return
            limit = self.guest_limit if user["mode"] == "guest" else self.plan_limit
            if user.get("plan_count", 0) >= limit:
                raise PlanQuotaError(
                    f"This workspace has reached its {limit}-plan limit. Remove a plan first."
                )
            doc = dict(
                schema_version=1,
                metadata=metadata,
                summary=summary,
                payload=payload,
                payload_sha256=digest,
            )
            if user.get("expires_at"):
                doc["expires_at"] = user["expires_at"]
            tx.create(ref, doc)
            tx.update(user_ref, {"plan_count": user.get("plan_count", 0) + 1})

        self._transaction(operation)

    def delete_plan(self, owner: str, plan_id: str) -> bool:
        user_ref = self._user(owner)
        ref = user_ref.collection("plans").document(plan_key(plan_id))

        def operation(tx):
            user_record = user_ref.get(transaction=tx, **_RPC)
            record = ref.get(transaction=tx, **_RPC)
            user = user_record.to_dict() if user_record.exists else None
            if not self._active(user, owner):
                raise InactiveWorkspaceError("This workspace expired or is being deleted.")
            if not record.exists:
                return False
            tx.delete(ref)
            tx.update(user_ref, {"plan_count": max(0, user.get("plan_count", 0) - 1)})
            return True

        return self._transaction(operation)

    def begin_deletion(self, owner: str):
        # A tombstone blocks writes while cleanup spans Auth and Firestore.
        self._user(owner).set(
            {"owner_uid": owner, "deleting": True, "deletion_requested_at": self.clock()},
            merge=True,
            **_RPC,
        )

    def delete_user_plans(self, owner: str):
        collection = self._user(owner).collection("plans")
        while True:
            docs = list(collection.limit(100).stream(**_RPC))
            if not docs:
                return
            batch = self.client.batch()
            for record in docs:
                batch.delete(record.reference)
            batch.commit(**_RPC)

    def finish_deletion(self, owner: str):
        self._user(owner).delete(**_RPC)

    def rate_allowed(self, key: str, limit=10, seconds=300) -> bool:
        if not 1 <= limit <= 10000 or not 1 <= seconds <= 86400:
            raise ValueError("Invalid rate limit")
        ref = self.client.collection("hb_throttle").document(
            hashlib.sha256(key.encode()).hexdigest()
        )
        now = self.clock()
        timestamp = now.timestamp()

        def operation(tx):
            record = ref.get(transaction=tx, **_RPC)
            history = (record.to_dict() or {}).get("events", []) if record.exists else []
            events = [t for t in history if t > timestamp - seconds]
            if len(events) >= limit:
                return False
            events.append(timestamp)
            tx.set(
                ref, {"events": events, "expires_at": now + timedelta(seconds=max(seconds, 3600))}
            )
            return True

        return self._transaction(operation)

    def revoke_session(self, cookie: str, expires_at: float):
        ref = self.client.collection("hb_revoked_sessions").document(
            hashlib.sha256(cookie.encode()).hexdigest()
        )
        ref.set({"expires_at": datetime.fromtimestamp(expires_at, UTC)}, **_RPC)

    def session_revoked(self, cookie: str) -> bool:
        ref = self.client.collection("hb_revoked_sessions").document(
            hashlib.sha256(cookie.encode()).hexdigest()
        )
        record = ref.get(**_RPC)
        return bool(record.exists and record.to_dict()["expires_at"] > self.clock())

    def cleanup_candidates(self, limit=100) -> list[str]:
        users = self.client.collection("hb_users")
        expired = users.where(filter=FieldFilter("expires_at", "<=", self.clock())).limit(limit)
        deleting = users.where(filter=FieldFilter("deleting", "==", True)).limit(limit)
        return list(
            dict.fromkeys(
                record.to_dict()["owner_uid"]
                for query in (expired, deleting)
                for record in query.stream(**_RPC)
            )
        )[:limit]

    def cleanup_expired_limits(self, limit=500) -> int:
        deleted = 0
        for name in ("hb_throttle", "hb_revoked_sessions"):
            records = (
                self.client.collection(name)
                .where(filter=FieldFilter("expires_at", "<=", self.clock()))
                .limit(min(limit, 500))
            )
            docs = list(records.stream(**_RPC))
            if docs:
                batch = self.client.batch()
                for record in docs:
                    batch.delete(record.reference)
                batch.commit(**_RPC)
                deleted += len(docs)
        return deleted
