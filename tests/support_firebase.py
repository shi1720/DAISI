"""Deterministic Firestore protocol double; no credentials or network are used.

Transactions serialize concurrent callers, enforce reads before writes, and only
commit after a successful callback. Live hosted smoke tests remain separate.
"""

from __future__ import annotations

import copy
import threading
from dataclasses import replace
from datetime import UTC, datetime

from hawkerbridge.config import Settings


def firebase_settings(**kwargs):
    return replace(
        Settings(),
        auth_mode="firebase",
        storage="firestore",
        secure_cookies=True,
        firebase_project="hawkerbridge",
        firebase_api_key="public-test-key",
        allowed_origins=("https://hawkerbridge-sg.web.app",),
        **kwargs,
    )


class Snapshot:
    def __init__(self, reference, data):
        self.reference = reference
        self.data = copy.deepcopy(data)
        self.exists = data is not None

    def to_dict(self):
        return copy.deepcopy(self.data)


class Document:
    def __init__(self, client, path):
        self.client, self.path = client, path

    def get(self, transaction=None, **kwargs):
        if transaction:
            assert not transaction.writes, "Firestore reads must precede writes"
        return Snapshot(self, self.client.docs.get(self.path))

    def collection(self, name):
        return Query(self.client, f"{self.path}/{name}")

    def set(self, data, merge=False, **kwargs):
        with self.client.lock:
            current = self.client.docs.get(self.path, {}) if merge else {}
            self.client.docs[self.path] = copy.deepcopy({**current, **data})

    def delete(self, **kwargs):
        with self.client.lock:
            self.client.docs.pop(self.path, None)


class Query:
    def __init__(self, client, path, *, fields=None, cap=None, filters=()):
        self.client, self.path = client, path
        self.fields, self.cap, self.filters = fields, cap, filters

    def document(self, identifier):
        return Document(self.client, f"{self.path}/{identifier}")

    def _copy(self, **kwargs):
        return Query(
            self.client,
            self.path,
            **({"fields": self.fields, "cap": self.cap, "filters": self.filters} | kwargs),
        )

    def select(self, fields):
        self.client.projections.append(tuple(fields))
        return self._copy(fields=fields)

    def limit(self, cap):
        return self._copy(cap=cap)

    def where(self, *, filter):
        return self._copy(filters=(*self.filters, filter))

    def stream(self, **kwargs):
        count = 0
        with self.client.lock:
            rows = copy.deepcopy(self.client.docs)
        for path, data in rows.items():
            if not path.startswith(self.path + "/") or "/" in path[len(self.path) + 1 :]:
                continue
            matches = True
            for item in self.filters:
                value = data.get(item.field_path)
                if (
                    value is None
                    or (item.op_string == "<=" and not value <= item.value)
                    or (item.op_string == "==" and value != item.value)
                ):
                    matches = False
            if not matches:
                continue
            if self.fields:
                data = {k: data[k] for k in self.fields if k in data}
            yield Snapshot(Document(self.client, path), data)
            count += 1
            if self.cap and count >= self.cap:
                break


class Transaction:
    def __init__(self, client):
        self.client, self.writes = client, []

    def create(self, ref, data):
        assert ref.path not in self.client.docs
        self.writes.append(("set", ref, copy.deepcopy(data)))

    def set(self, ref, data):
        self.writes.append(("set", ref, copy.deepcopy(data)))

    def update(self, ref, data):
        assert ref.path in self.client.docs
        self.writes.append(("update", ref, copy.deepcopy(data)))

    def delete(self, ref):
        self.writes.append(("delete", ref, None))

    def commit(self, **kwargs):
        for operation, ref, data in self.writes:
            if operation == "delete":
                ref.delete()
            else:
                ref.set(data, merge=operation == "update")


def transactional(function):
    def execute(tx):
        with tx.client.lock:
            result = function(tx)
            tx.commit()
            return result

    return execute


class MemoryFirestore:
    def __init__(self):
        self.docs = {}
        self.lock = threading.RLock()
        self.projections = []

    def collection(self, name):
        return Query(self, name)

    def transaction(self, **kwargs):
        return Transaction(self)

    def batch(self):
        return Transaction(self)


class Clock:
    def __init__(self):
        self.now = datetime(2026, 9, 22, 12, tzinfo=UTC)

    def __call__(self):
        return self.now


def example_plan(identifier="plan-one"):
    return dict(
        id=identifier,
        title="Closure support",
        status="draft",
        date="2026-09-28",
        created_at="2026-09-22T12:00:00+00:00",
        updated_at="2026-09-22T12:00:00+00:00",
        parameters={"date": "2026-09-28", "budget": 1500},
        notes="Private planning notes",
        result={"summary": {"allocated_meals": 225}, "zones": [{"id": "A", "geometry": {}}]},
        source_manifest={"sources": ["verified-source"]},
        engine_code_sha256="abc123",
    )
