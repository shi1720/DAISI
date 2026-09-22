"""Security and complete workflow tests against real source data and isolated storage."""

from __future__ import annotations

import hashlib
import io
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from hawkerbridge.api import create_app
from hawkerbridge.config import Settings
from pypdf import PdfReader


@pytest.fixture
def client(tmp_path):
    app = create_app(replace(Settings(), database_path=tmp_path / "test.db"))
    with TestClient(app) as c:
        yield c


def guest(client):
    r = client.post("/api/auth/demo", json={})
    assert r.status_code == 200
    client.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return r.json()


def test_unauthenticated_data_not_accessible(client):
    assert client.get("/api/health").json()["status"] == "ready"
    assert client.get("/api/snapshot").status_code == 401
    assert client.get("/api/plans").status_code == 401


def test_secure_session_and_csrf(client):
    response = client.post("/api/auth/demo", json={})
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=lax" in response.headers["set-cookie"]
    assert client.post("/api/optimise", json={"date": "2026-09-22"}).status_code == 403
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    assert client.post("/api/analyse", json={"date": "2026-09-22"}).status_code == 200
    assert client.post("/api/auth/logout", json={}).status_code == 204
    assert client.get("/api/plans").status_code == 401


def test_cross_origin_login_and_compute_are_blocked(client):
    assert (
        client.post(
            "/api/auth/demo", json={}, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    assert (
        client.post("/api/auth/demo", json={}, headers={"Sec-Fetch-Site": "cross-site"}).status_code
        == 403
    )
    assert (
        client.post(
            "/api/auth/demo", json={}, headers={"Origin": "http://localhost:8000"}
        ).status_code
        == 200
    )


def test_registration_login_rotation_and_account_deletion(client):
    payload = dict(
        name="Sample planner", email="PLANNER@example.com", password="a-long-test-password"
    )
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 201
    assert r.json()["user"]["email"] == "planner@example.com"
    old_cookie = client.cookies.get("hb_session")
    client.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    assert client.post("/api/auth/register", json=payload).status_code == 409
    client.post("/api/auth/logout", json={})
    assert (
        client.post(
            "/api/auth/login", json={"email": payload["email"], "password": "wrong"}
        ).status_code
        == 401
    )
    r = client.post(
        "/api/auth/login", json={"email": payload["email"], "password": payload["password"]}
    )
    assert r.status_code == 200
    assert client.cookies.get("hb_session") != old_cookie
    client.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    assert client.delete("/api/auth/account").status_code == 204
    assert client.get("/api/auth/session").json()["user"] is None


def test_validation_rejects_bad_inputs(client):
    guest(client)
    for params in [
        dict(date="2026-09-22", budget=-1),
        dict(date="bad"),
        dict(date="2026-09-22", participation_rate=2),
        dict(date="2026-09-22", budget=1.001),
        dict(date="2027-09-22"),
        dict(date="2026-09-22", rescheduled_closure_ids=["not-a-closure"]),
        dict(date="2026-09-22", unknown=1),
    ]:
        assert client.post("/api/optimise", json=params).status_code == 422
    assert (
        client.post(
            "/api/auth/register", json=dict(name="User", email="a@b.com", password="short")
        ).status_code
        == 422
    )


def test_complete_plan_workflow_and_exports(client):
    guest(client)
    r = client.post(
        "/api/plans",
        json=dict(
            title="Clementi plan <script>",
            parameters={"date": "2026-09-22"},
            notes='=HYPERLINK("https://example.com")',
        ),
    )
    assert r.status_code == 201
    plan = r.json()
    pid = plan["id"]
    assert plan["status"] == "draft"
    assert plan["result"]["summary"]["spent"] <= 1500
    assert client.get("/api/plans").json()["plans"][0]["id"] == pid
    assert client.get(f"/api/plans/{pid}").json()["parameters"]["date"] == "2026-09-22"
    r = client.patch(f"/api/plans/{pid}", json={"status": "reviewed"})
    assert r.json()["reviewed_by"] == "Demo planner"
    assert client.get(f"/api/brief?plan_id={pid}").json()["method"].startswith("Deterministic")
    exported = client.get(f"/api/plans/{pid}/export?format=json")
    assert exported.json()["id"] == pid
    csv = client.get(f"/api/plans/{pid}/export?format=csv")
    assert "'=HYPERLINK" in csv.text
    pdf = client.get(f"/api/plans/{pid}/export?format=pdf")
    assert pdf.content.startswith(b"%PDF")
    text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
    assert "Clementi plan <script>" in text
    assert "Before implementation" in text
    assert "Snapshot SHA256" in text
    assert client.get(f"/api/plans/{pid}/export?format=exe").status_code == 422
    assert client.delete(f"/api/plans/{pid}").status_code == 204
    assert client.get(f"/api/plans/{pid}").status_code == 404


def test_cross_account_plan_isolation(client):
    guest(client)
    plan = client.post(
        "/api/plans", json={"title": "Private planning notes", "parameters": {"date": "2026-09-22"}}
    ).json()
    pid = plan["id"]
    client.post("/api/auth/logout", json={})
    guest(client)
    assert client.get("/api/plans").json()["plans"] == []
    assert client.get(f"/api/plans/{pid}").status_code == 404
    assert client.get(f"/api/plans/{pid}/export?format=json").status_code == 404
    assert client.patch(f"/api/plans/{pid}", json={"status": "reviewed"}).status_code == 404
    assert client.delete(f"/api/plans/{pid}").status_code == 404
    assert client.get(f"/api/brief?plan_id={pid}").status_code == 404


def test_headers_and_unknown_endpoint(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'self'" in r.headers["content-security-policy"]
    assert r.headers["cache-control"] == "no-store"
    assert client.get("/api/not-real").status_code == 404


def test_password_is_hashed_and_session_tokens_not_stored_raw(client):
    r = client.post(
        "/api/auth/register",
        json={"name": "Test user", "email": "test@example.com", "password": "12-good-password"},
    )
    assert r.status_code == 201
    token = client.cookies.get("hb_session")
    db = client.app.state.settings.database_path
    content = db.read_bytes()
    assert b"12-good-password" not in content
    assert token.encode() not in content
    with client.app.state.store.connect() as conn:
        assert (
            conn.execute("SELECT password_hash FROM users").fetchone()[0].startswith("$argon2id$")
        )


def test_rate_limit(client):
    for _ in range(12):
        client.post("/api/auth/login", json={"email": "missing@example.com", "password": "invalid"})
    r = client.post("/api/auth/login", json={"email": "missing@example.com", "password": "invalid"})
    assert r.status_code == 429
    assert "retry-after" in r.headers


def test_readonly_dataset_and_evidence_are_linked(client):
    guest(client)
    snapshot = client.get("/api/snapshot").json()
    evidence = client.get("/api/evidence").json()
    assert snapshot["manifest"]["population_year"] == 2020
    assert evidence["manifest"]["quality"]["quarantined_closure_intervals"] > 0
    assert evidence["methodology"]["version"] == "hawkerbridge-1.0.0"
    assert all(x["url"].startswith("https://data.gov.sg") for x in evidence["manifest"]["sources"])


def test_saved_provenance_survives_restart_with_new_published_inputs(tmp_path):
    """A historical plan must never acquire the next snapshot's evidence."""
    original = json.loads(Settings().data_path.read_text())
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(json.dumps(original))
    settings = replace(
        Settings(), data_path=snapshot_path, database_path=tmp_path / "persistent.db"
    )
    with TestClient(create_app(settings)) as first:
        guest(first)
        response = first.post(
            "/api/plans",
            json={"title": "Before the data refresh", "parameters": {"date": "2026-09-22"}},
        )
        assert response.status_code == 201
        saved = response.json()
        assert saved["source_manifest"] == original["manifest"]
        assert len(saved["engine_code_sha256"]) == 64
        cookie = first.cookies.get("hb_session")
        old_fingerprint = first.get("/api/health").json()["source_fingerprint"]

    # Simulate a later publication without changing the committed source archive.
    refreshed = deepcopy(original)
    refreshed["manifest"]["fetched_at"] = "2026-09-23T12:00:00+00:00"
    refreshed["manifest"]["sources"][0]["sha256"] = "f" * 64
    snapshot_path.write_text(json.dumps(refreshed))
    with TestClient(create_app(settings)) as second:
        second.cookies.set("hb_session", cookie)
        assert second.get("/api/health").json()["source_fingerprint"] != old_fingerprint
        assert second.get("/api/snapshot").json()["manifest"] == refreshed["manifest"]
        plan_id = saved["id"]
        persisted = second.get(f"/api/plans/{plan_id}")
        assert persisted.status_code == 200
        assert persisted.json() == saved
        exported = second.get(f"/api/plans/{plan_id}/export?format=json").json()
        assert exported["source_manifest"] == original["manifest"]
        assert exported["result"]["source_fingerprint"] == old_fingerprint
        assert exported["engine_code_sha256"] == saved["engine_code_sha256"]
        brief = second.get("/api/brief", params={"plan_id": plan_id}).json()
        assert brief["evidence_status"] == "preserved"
        assert brief["sources"] == original["manifest"]["sources"]
        assert brief["sources"] != refreshed["manifest"]["sources"]


@pytest.mark.parametrize("change", ["none", "input", "engine", "unversioned"])
def test_evaluation_is_current_only_for_matching_inputs_and_engine(
    client, tmp_path, monkeypatch, change
):
    from hawkerbridge import api as api_module

    guest(client)
    report = {
        "source_fingerprint": client.get("/api/health").json()["source_fingerprint"],
        "engine_code_sha256": hashlib.sha256(
            Path(api_module.__file__).with_name("engine.py").read_bytes()
        ).hexdigest(),
        "scenarios_evaluated": 1,
        "results": [{"scenario_id": "isolated-test-report"}],
    }
    if change == "input":
        report["source_fingerprint"] = "0" * 64
    elif change == "engine":
        report["engine_code_sha256"] = "0" * 64
    elif change == "unversioned":
        report.pop("engine_code_sha256")
    evaluation_path = tmp_path / "data/processed/evaluation.json"
    evaluation_path.parent.mkdir(parents=True)
    evaluation_path.write_text(json.dumps(report))
    # Redirect the evaluation artifact only; the app still uses real loaded inputs.
    monkeypatch.setattr(api_module, "ROOT", tmp_path)
    response = client.get("/api/evidence")
    assert response.status_code == 200
    evidence = response.json()
    if change == "none":
        assert evidence["evaluation_status"] == "current"
        assert evidence["evaluation"] == report
    else:
        assert evidence["evaluation_status"] == "stale"
        assert evidence["evaluation"] is None


@pytest.mark.parametrize("field", ["title", "notes"])
def test_editing_reviewed_plan_requires_fresh_review(client, field):
    guest(client)
    created = client.post(
        "/api/plans",
        json={"title": "Review lifecycle", "parameters": {"date": "2026-09-22"}},
    )
    assert created.status_code == 201
    saved = created.json()
    url = f"/api/plans/{saved['id']}"
    reviewed = client.patch(url, json={"status": "reviewed"}).json()
    assert reviewed["status"] == "reviewed"
    assert reviewed["reviewed_by"] == "Demo planner" and reviewed["reviewed_at"]
    changed = client.patch(url, json={field: "Changed after review"})
    assert changed.status_code == 200
    for plan in (
        changed.json(),
        client.get(url).json(),
        client.get(url + "/export?format=json").json(),
    ):
        assert plan["status"] == "draft"
        assert "reviewed_by" not in plan and "reviewed_at" not in plan
        assert plan[field] == "Changed after review"
        assert plan["result"] == saved["result"]
        assert plan["source_manifest"] == saved["source_manifest"]
    rereviewed = client.patch(url, json={"status": "reviewed"}).json()
    assert rereviewed["status"] == "reviewed"
    assert rereviewed["reviewed_by"] == "Demo planner"
