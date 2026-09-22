"""Workspace proxy mode must fail closed and isolate plans by trusted identity."""

import copy
import json
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from hawkerbridge.api import create_app
from hawkerbridge.config import Settings


def test_workspace_mode_cannot_be_enabled_accidentally(monkeypatch):
    for key in [
        "DATABRICKS_APP_NAME",
        "DATABRICKS_APP_PORT",
        "DATABRICKS_WORKSPACE_ID",
        "DATABRICKS_HOST",
    ]:
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValueError, match="managed Databricks Apps"):
        replace(
            Settings(), auth_mode="databricks", storage="databricks", databricks_warehouse_id="test"
        ).validate()


def test_local_mode_ignores_forged_workspace_identity(tmp_path):
    app = create_app(replace(Settings(), database_path=tmp_path / "local.db"))
    with TestClient(app) as client:
        response = client.get(
            "/api/auth/session",
            headers={"X-Forwarded-User": "admin", "X-Forwarded-Email": "admin@example.test"},
        )
        assert response.json()["user"] is None
        assert client.get("/api/plans", headers={"X-Forwarded-User": "admin"}).status_code == 401


def test_proxy_identity_csrf_isolation_and_no_local_registration(monkeypatch, tmp_path):
    from hawkerbridge import databricks_store

    settings = replace(
        Settings(),
        database_path=tmp_path / "unused.db",
        auth_mode="databricks",
        storage="databricks",
        databricks_warehouse_id="test",
    )
    for key, value in {
        "DATABRICKS_APP_NAME": "hawkerbridge",
        "DATABRICKS_APP_PORT": "8000",
        "DATABRICKS_WORKSPACE_ID": "123",
        "DATABRICKS_HOST": "https://workspace.example.test",
    }.items():
        monkeypatch.setenv(key, value)
    snapshot = json.loads(settings.data_path.read_text())

    class FakeStore:
        def __init__(self, config):
            self.plans = {}

        def load_snapshot(self):
            return snapshot

        def list_plans(self, owner_id):
            return [copy.deepcopy(p) for (o, _), p in self.plans.items() if o == owner_id]

        def get_plan(self, owner_id, plan_id):
            return copy.deepcopy(self.plans.get((owner_id, plan_id)))

        def save_plan(self, owner_id, plan):
            self.plans[(owner_id, plan["id"])] = copy.deepcopy(plan)

        def delete_plan(self, owner_id, plan_id):
            return self.plans.pop((owner_id, plan_id), None) is not None

    monkeypatch.setattr(databricks_store, "DatabricksStore", FakeStore)
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/plans").status_code == 401
        assert client.post("/api/auth/demo", json={}).status_code == 403
        assert (
            client.post(
                "/api/auth/register",
                json={
                    "name": "Tester",
                    "email": "a@example.test",
                    "password": "long-enough-password",
                },
            ).status_code
            == 403
        )
        client.headers.update(
            {"X-Forwarded-User": "subject-A", "X-Forwarded-Email": "a@example.test"}
        )
        info = client.get("/api/auth/session").json()
        assert info["user"]["mode"] == "databricks"
        assert (
            client.post(
                "/api/plans", json={"title": "A plan", "parameters": {"date": "2026-09-28"}}
            ).status_code
            == 403
        )
        client.headers["X-CSRF-Token"] = info["csrf_token"]
        response = client.post(
            "/api/plans", json={"title": "A plan", "parameters": {"date": "2026-09-28"}}
        )
        assert response.status_code == 201
        plan = response.json()
        client.headers.update(
            {"X-Forwarded-User": "subject-B", "X-Forwarded-Email": "b@example.test"}
        )
        assert client.get("/api/plans").json() == {"plans": []}
        assert client.get(f"/api/plans/{plan['id']}").status_code == 404
        assert client.post("/api/optimise", json={"date": "2026-09-28"}).status_code == 403
        b = client.get("/api/auth/session").json()
        assert b["csrf_token"] != info["csrf_token"]
        client.headers["X-CSRF-Token"] = b["csrf_token"]
        assert client.post("/api/optimise", json={"date": "2026-09-28"}).status_code == 200
        assert not settings.database_path.exists()
