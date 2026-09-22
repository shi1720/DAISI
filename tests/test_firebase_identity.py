from __future__ import annotations

import json
import time
from dataclasses import replace

import httpx
import pytest
from firebase_admin import auth
from hawkerbridge.firebase_identity import FirebaseIdentity, FirebaseIdentityError, csrf_for_session
from support_firebase import firebase_settings


def identity(handler):
    return FirebaseIdentity(
        firebase_settings(), app=object(), http=httpx.Client(transport=httpx.MockTransport(handler))
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"storage": "local"},
        {"auth_mode": "local"},
        {"secure_cookies": False},
        {"firebase_project": ""},
        {"firebase_api_key": ""},
        {"allowed_origins": ()},
        {"allowed_origins": ("http://example.com",)},
        {"allowed_origins": ("https://example.com/path",)},
        {"allowed_origins": ("https://*.example.com",)},
        {"allowed_origins": ("https://user:password@example.com",)},
        {"auth_attempts_per_5_minutes": 0},
        {"guest_sessions_per_hour": 1001},
        {"password_resets_per_hour": 2},
    ],
)
def test_public_configuration_fails_closed(changes):
    with pytest.raises(ValueError):
        replace(firebase_settings(), **changes).validate()


def test_explicit_project_and_valid_settings(monkeypatch):
    from hawkerbridge import firebase_identity

    seen = {}
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "other-host-project")
    monkeypatch.setattr(
        firebase_identity.firebase_admin,
        "get_app",
        lambda name: (_ for _ in ()).throw(ValueError()),
    )

    def initialize_app(**kwargs):
        seen.update(kwargs)
        return "explicit-app"

    monkeypatch.setattr(firebase_identity.firebase_admin, "initialize_app", initialize_app)
    assert firebase_identity.firebase_app("hawkerbridge") == "explicit-app"
    assert seen == {"options": {"projectId": "hawkerbridge"}, "name": "hawkerbridge-hawkerbridge"}
    firebase_settings().validate()
    assert "public-test-key" not in repr(firebase_settings())


def test_registration_uses_provider_password_and_recent_verified_token(monkeypatch):
    requests, verified, issued = [], [], []

    def handler(request):
        requests.append((request.url.path, json.loads(request.content)))
        return httpx.Response(200, json={"localId": "user-one", "idToken": "provider-token"})

    claims = dict(
        uid="user-one",
        email="planner@example.com",
        name="Planner",
        auth_time=time.time(),
        firebase={"sign_in_provider": "password"},
    )

    def verify(token, **kwargs):
        verified.append((token, kwargs))
        return claims

    def issue(token, **kwargs):
        issued.append((token, kwargs))
        return "opaque-session"

    monkeypatch.setattr(auth, "verify_id_token", verify)
    monkeypatch.setattr(auth, "create_session_cookie", issue)
    service = identity(handler)
    token, user, _ = service.register("Planner", "planner@example.com", "a-long-password")
    assert token == "opaque-session" and user["mode"] == "firebase"
    assert requests[0][1]["password"] == "a-long-password"
    assert requests[1][1]["displayName"] == "Planner"
    assert verified[0][1]["check_revoked"] is True
    assert issued[0][1]["expires_in"].total_seconds() == 43200
    assert csrf_for_session(token) == csrf_for_session(token)
    assert csrf_for_session(token) != csrf_for_session("another-session")


def test_stale_id_token_cannot_be_exchanged_for_session(monkeypatch):
    monkeypatch.setattr(
        auth,
        "verify_id_token",
        lambda *args, **kwargs: {"uid": "one", "auth_time": time.time() - 600},
    )
    service = identity(lambda request: httpx.Response(200, json={"idToken": "token"}))
    with pytest.raises(FirebaseIdentityError) as error:
        service.login("a@example.com", "password")
    assert error.value.status_code == 401


@pytest.mark.parametrize(
    "provider_error",
    ["EMAIL_NOT_FOUND", "INVALID_PASSWORD", "INVALID_LOGIN_CREDENTIALS", "USER_DISABLED"],
)
def test_login_errors_do_not_enumerate_accounts(provider_error):
    service = identity(
        lambda request: httpx.Response(400, json={"error": {"message": provider_error}})
    )
    with pytest.raises(FirebaseIdentityError) as error:
        service.login("a@example.com", "password")
    assert error.value.status_code == 401
    assert str(error.value) == "Email or password is incorrect."


@pytest.mark.parametrize("provider_error", ["EMAIL_NOT_FOUND", "USER_DISABLED", "INVALID_EMAIL"])
def test_password_reset_is_generic_for_missing_or_disabled_accounts(provider_error):
    service = identity(
        lambda request: httpx.Response(400, json={"error": {"message": provider_error}})
    )
    assert service.reset_password("a@example.com") is None


def test_session_verification_checks_revocation_and_rejects_forgery(monkeypatch):
    calls = []

    def verify(token, **kwargs):
        calls.append(kwargs)
        if token != "valid":
            raise ValueError("forged")
        return {"uid": "one"}

    monkeypatch.setattr(auth, "verify_session_cookie", verify)
    service = identity(lambda _: httpx.Response(200, json={}))
    assert service.verify("valid") == {"uid": "one"}
    assert service.verify("forged") is None
    assert service.verify("x" * 12001) is None
    assert service.verify(None) is None
    assert len(calls) == 2 and all(call["check_revoked"] for call in calls)


def test_provider_outage_does_not_expose_response_secrets():
    service = identity(lambda request: httpx.Response(500, text="secret upstream trace"))
    with pytest.raises(FirebaseIdentityError) as error:
        service.login("a@example.com", "password")
    assert error.value.status_code == 503
    assert "secret" not in str(error.value)


def test_incomplete_registration_is_cleaned_up(monkeypatch):
    count, deleted = 0, []

    def handler(request):
        nonlocal count
        count += 1
        return (
            httpx.Response(200, json={"localId": "new-user", "idToken": "one"})
            if count == 1
            else httpx.Response(503, json={})
        )

    service = identity(handler)
    monkeypatch.setattr(service, "delete_user", deleted.append)
    with pytest.raises(FirebaseIdentityError):
        service.register("Planner", "a@example.com", "password")
    assert deleted == ["new-user"]
