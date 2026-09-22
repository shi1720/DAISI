"""Hosted API contract with real planner/store, mocked Google identity/transport."""

from __future__ import annotations

import secrets
import time
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from hawkerbridge.api import create_app
from hawkerbridge.firebase_identity import FirebaseIdentityError
from hawkerbridge.firestore_store import FirestoreStore
from support_firebase import Clock, MemoryFirestore, example_plan, firebase_settings, transactional

ORIGIN = "https://hawkerbridge-sg.web.app"


class FakeIdentity:
    app = object()

    def __init__(self):
        self.tokens, self.accounts, self.reset_emails = {}, {}, []
        self.deleted, self.disabled = set(), set()

    def _issue(self, uid, name="Planner", email="planner@example.com", mode="firebase"):
        token = secrets.token_urlsafe(32)
        user = dict(id=uid, name=name, email=email, mode=mode)
        claims = {"uid": uid, "exp": time.time() + 43200, "user": user}
        self.tokens[token] = claims
        return token, user, claims

    def user(self, claims):
        return deepcopy(claims["user"])

    def register(self, name, email, password):
        if email in self.accounts:
            raise FirebaseIdentityError(409, "An account already uses that email. Try signing in.")
        uid = "user-" + secrets.token_hex(4)
        self.accounts[email] = (uid, name, password)
        return self._issue(uid, name, email)

    def login(self, email, password):
        record = self.accounts.get(email)
        if not record or record[2] != password or record[0] in self.disabled:
            raise FirebaseIdentityError(401, "Email or password is incorrect.")
        return self._issue(record[0], record[1], email)

    def guest(self):
        return self._issue("guest-" + secrets.token_hex(4), "Demo planner", "", "guest")

    def verify(self, token):
        claims = self.tokens.get(token)
        return (
            deepcopy(claims)
            if claims and claims["uid"] not in self.disabled | self.deleted
            else None
        )

    def reset_password(self, email):
        self.reset_emails.append(email)

    def disable_user(self, uid):
        self.disabled.add(uid)

    def delete_user(self, uid):
        self.deleted.add(uid)

    def close(self):
        pass


@pytest.fixture
def hosted(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "hawkerbridge.firestore_store.google_firestore.transactional", transactional
    )
    settings = firebase_settings(database_path=tmp_path / "must-not-exist.db")
    clock, client, identity = Clock(), MemoryFirestore(), FakeIdentity()
    store = FirestoreStore(settings, client=client, clock=clock)
    monkeypatch.setattr(
        "hawkerbridge.firebase_identity.FirebaseIdentity", lambda settings: identity
    )
    monkeypatch.setattr(
        "hawkerbridge.firestore_store.FirestoreStore", lambda *args, **kwargs: store
    )
    return settings, store, identity


def client(hosted):
    return TestClient(create_app(hosted[0]), base_url=ORIGIN, headers={"Origin": ORIGIN})


def register(c, email="planner@example.com"):
    response = c.post(
        "/api/auth/register",
        json={"name": "Planner", "email": email, "password": "a-long-test-password"},
    )
    assert response.status_code == 201, response.text
    c.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return response


def test_cookie_cross_instance_csrf_and_saved_workspace_survive_restart(hosted):
    with client(hosted) as first, client(hosted) as second:
        registered = register(first)
        cookie = first.cookies.get("__session")
        header = registered.headers["set-cookie"]
        assert header.startswith("__session=")
        assert all(flag in header for flag in ("HttpOnly", "Secure", "SameSite=lax"))
        assert "hb_session" not in header
        second.cookies.set("__session", cookie)
        session = second.get("/api/auth/session").json()
        assert session["csrf_token"] == first.headers["X-CSRF-Token"]
        second.headers["X-CSRF-Token"] = session["csrf_token"]
        saved = second.post(
            "/api/plans", json={"title": "Closure plan", "parameters": {"date": "2026-09-28"}}
        )
        assert saved.status_code == 201, saved.text
        assert saved.json()["result"]["summary"]["total_meals"] == 225
        assert first.get("/api/plans").json()["plans"][0]["id"] == saved.json()["id"]
        assert not hosted[0].database_path.exists()
        assert first.get(f"/api/plans/{saved.json()['id']}/export?format=pdf").content.startswith(
            b"%PDF"
        )


def test_exact_origins_missing_origin_forged_identity_and_csrf(hosted):
    with client(hosted) as c:
        c.headers.pop("origin")
        assert c.post("/api/auth/demo", json={}).status_code == 403
        for headers in (
            {"Origin": "https://evil.example", "Host": "evil.example"},
            {"Origin": "https://evil.example", "X-Forwarded-Host": "evil.example"},
            {"Origin": ORIGIN, "Sec-Fetch-Site": "cross-site"},
        ):
            response = c.post("/api/auth/demo", json={}, headers=headers)
            assert response.status_code == 403
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["x-content-type-options"] == "nosniff"
        assert (
            c.get(
                "/api/auth/session",
                headers={"X-Forwarded-User": "admin", "X-Forwarded-Email": "admin@example.com"},
            ).json()["user"]
            is None
        )
        c.headers["Origin"] = ORIGIN
        register(c)
        c.headers["X-CSRF-Token"] = "wrong"
        assert c.delete("/api/auth/account").status_code == 403
        assert not hosted[2].deleted


def test_owner_isolation_and_logout_prevents_cookie_replay(hosted):
    with client(hosted) as a, client(hosted) as b:
        uid = register(a).json()["user"]["id"]
        register(b, "other@example.com")
        hosted[1].save_plan(uid, example_plan())
        assert b.get("/api/plans/plan-one").status_code == 404
        assert (
            b.patch(
                "/api/plans/plan-one",
                json={"title": "hacked", "expected_updated_at": example_plan()["updated_at"]},
            ).status_code
            == 404
        )
        assert b.delete("/api/plans/plan-one").status_code == 404
        assert b.get("/api/plans/plan-one/export").status_code == 404
        token = a.cookies.get("__session")
        assert a.post("/api/auth/logout").status_code == 204
        a.cookies.set("__session", token)
        assert a.get("/api/plans").status_code == 401
        assert b.get("/api/plans").status_code == 200
        assert hosted[1].get_plan(uid, "plan-one") is not None


def test_own_account_and_guest_logout_delete_auth_and_all_owned_data(hosted):
    with client(hosted) as c:
        uid = register(c).json()["user"]["id"]
        hosted[1].save_plan(uid, example_plan())
        response = c.delete("/api/auth/account")
        assert response.status_code == 204
        assert "__session" not in c.cookies
        assert uid in hosted[2].deleted
        assert not hosted[1]._user(uid).get().exists
        assert hosted[1].list_plans(uid) == []
        demo = c.post("/api/auth/demo", json={}).json()
        c.headers["X-CSRF-Token"] = demo["csrf_token"]
        guest = demo["user"]["id"]
        hosted[1].save_plan(guest, example_plan())
        assert c.post("/api/auth/logout").status_code == 204
        assert guest in hosted[2].deleted
        assert not hosted[1]._user(guest).get().exists


def test_expired_guests_rejected_and_password_reset_response_is_generic(hosted):
    with client(hosted) as c:
        assert c.post("/api/auth/demo", json={}).status_code == 200
        hosted[1].clock.now += timedelta(days=7)
        assert c.get("/api/plans").status_code == 401
        response = c.post("/api/auth/reset-password", json={"email": "UNKNOWN@example.com"})
        assert response.status_code == 200
        assert response.json() == {
            "message": "If an account uses that email, a password reset link will be sent."
        }
        assert hosted[2].reset_emails == ["unknown@example.com"]
        for _ in range(2):
            assert (
                c.post(
                    "/api/auth/reset-password", json={"email": "unknown@example.com"}
                ).status_code
                == 200
            )
        assert (
            c.post("/api/auth/reset-password", json={"email": "unknown@example.com"}).status_code
            == 429
        )


def test_managed_database_outage_is_fail_closed(hosted, monkeypatch):
    from google.api_core.exceptions import ServiceUnavailable

    with client(hosted) as c:
        register(c)
        monkeypatch.setattr(
            hosted[1],
            "user_active",
            lambda _: (_ for _ in ()).throw(ServiceUnavailable("secret provider detail")),
        )
        response = c.get("/api/plans")
        assert response.status_code == 503
        assert "secret" not in response.text
        assert response.headers["cache-control"] == "no-store"


def test_public_service_quotas_do_not_treat_shared_proxy_as_one_visitor(hosted):
    # Thirty unrelated visitors can share the same proxy peer; the old 20/hour
    # peer bucket would reject the last ten despite ample service capacity.
    for _ in range(30):
        with client(hosted) as c:
            response = c.post("/api/auth/demo", json={})
            assert response.status_code == 200
            c.headers["X-CSRF-Token"] = response.json()["csrf_token"]
            assert c.post("/api/auth/logout").status_code == 204


def test_public_quota_is_configurable_and_shared_across_instances(hosted):
    limited = (replace(hosted[0], guest_sessions_per_hour=5), *hosted[1:])
    for index in range(6):
        with client(limited) as c:
            response = c.post("/api/auth/demo", json={})
            assert response.status_code == (200 if index < 5 else 429)
            if index == 5:
                assert response.headers["retry-after"] == "3600"


def test_signup_email_limit_is_shared_and_attempts_do_not_reveal_password(hosted):
    for index in range(6):
        with client(hosted) as c:
            response = c.post(
                "/api/auth/register",
                json={
                    "name": "Planner",
                    "email": "same@example.com",
                    "password": "a-long-test-password",
                },
            )
            assert response.status_code == (201 if index == 0 else 409 if index < 5 else 429)
            assert "a-long-test-password" not in response.text


def test_hosted_two_tabs_require_current_revision_before_review(hosted):
    with client(hosted) as c:
        uid = register(c).json()["user"]["id"]
        hosted[1].save_plan(uid, example_plan())
        original = c.get("/api/plans/plan-one").json()
        changed = c.patch(
            "/api/plans/plan-one",
            json={"notes": "A newer instruction", "expected_updated_at": original["updated_at"]},
        )
        assert changed.status_code == 200
        stale = c.patch(
            "/api/plans/plan-one",
            json={"status": "reviewed", "expected_updated_at": original["updated_at"]},
        )
        assert stale.status_code == 409
        assert "another tab" in stale.json()["detail"]
        current = c.get("/api/plans/plan-one").json()
        assert current["notes"] == "A newer instruction" and current["status"] == "draft"
        assert (
            c.patch(
                "/api/plans/plan-one",
                json={"status": "reviewed", "expected_updated_at": current["updated_at"]},
            ).status_code
            == 200
        )


def test_failed_workspace_initialization_removes_new_auth_user(hosted, monkeypatch):
    from google.api_core.exceptions import ServiceUnavailable

    monkeypatch.setattr(
        hosted[1], "ensure_user", lambda _: (_ for _ in ()).throw(ServiceUnavailable("offline"))
    )
    with client(hosted) as c:
        response = c.post("/api/auth/demo", json={})
        assert response.status_code == 503
        assert "__session" not in c.cookies
        assert len(hosted[2].deleted) == 1


def test_partial_account_delete_returns_error_and_blocks_access_until_cleanup(hosted, monkeypatch):
    with client(hosted) as c:
        uid = register(c).json()["user"]["id"]
        hosted[1].save_plan(uid, example_plan())

        def unavailable(owner):
            raise FirebaseIdentityError(
                503, "Account deletion could not be completed. Please retry."
            )

        monkeypatch.setattr(hosted[2], "delete_user", unavailable)
        assert c.delete("/api/auth/account").status_code == 503
        assert c.get("/api/plans").status_code == 401
        assert uid in hosted[1].cleanup_candidates()
        assert hosted[1].list_plans(uid) == []
