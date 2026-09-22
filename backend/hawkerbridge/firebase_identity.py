"""Firebase Authentication with managed credentials and server-side session cookies.

Password values pass directly to Google's REST API and are never persisted here.
Only Firebase Admin verifies identity. Workspace forwarding headers are irrelevant.
"""

from __future__ import annotations

import hashlib
import threading
import time
from datetime import timedelta

import firebase_admin
import httpx
from firebase_admin import auth, exceptions

_APP_LOCK = threading.Lock()


class FirebaseIdentityError(RuntimeError):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(message)


def firebase_app(project: str):
    """Explicit project prevents accidentally using the Cloud Run host project."""
    name = "hawkerbridge-" + project
    with _APP_LOCK:
        try:
            return firebase_admin.get_app(name)
        except ValueError:
            return firebase_admin.initialize_app(options={"projectId": project}, name=name)


def csrf_for_session(cookie: str) -> str:
    # The unpredictable, authenticated HttpOnly cookie is the binding secret.
    # No instance-local key: requests can reach any revision or instance.
    return hashlib.sha256(b"hawkerbridge-csrf-v1\0" + cookie.encode()).hexdigest()


class FirebaseIdentity:
    def __init__(self, settings, *, app=None, http=None):
        self.app = app or firebase_app(settings.firebase_project)
        self.api_key = settings.firebase_api_key
        self.hours = settings.session_hours
        self.http = http or httpx.Client(
            timeout=httpx.Timeout(15, connect=5),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )

    def close(self):
        self.http.close()

    def _request(self, action: str, payload: dict, *, reset=False) -> dict:
        try:
            response = self.http.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:{action}",
                params={"key": self.api_key},
                json=payload,
            )
        except httpx.RequestError as error:
            raise FirebaseIdentityError(
                503, "Sign-in service is temporarily unavailable."
            ) from error
        try:
            body = response.json()
        except ValueError as error:
            raise FirebaseIdentityError(
                503, "Sign-in service returned an invalid response."
            ) from error
        if response.is_success and isinstance(body, dict):
            return body
        code = str(body.get("error", {}).get("message", "")) if isinstance(body, dict) else ""
        code = code.split(" : ")[0]
        if reset and code in {"EMAIL_NOT_FOUND", "INVALID_EMAIL", "USER_DISABLED"}:
            return {}
        if code in {
            "EMAIL_NOT_FOUND",
            "INVALID_PASSWORD",
            "INVALID_LOGIN_CREDENTIALS",
            "USER_DISABLED",
        }:
            raise FirebaseIdentityError(401, "Email or password is incorrect.")
        if code == "EMAIL_EXISTS":
            raise FirebaseIdentityError(409, "An account already uses that email. Try signing in.")
        if code in {"TOO_MANY_ATTEMPTS_TRY_LATER", "QUOTA_EXCEEDED", "RESET_PASSWORD_EXCEED_LIMIT"}:
            raise FirebaseIdentityError(429, "Too many attempts. Please try again later.")
        if code in {"WEAK_PASSWORD", "INVALID_EMAIL"}:
            raise FirebaseIdentityError(422, "Use a valid email and a stronger password.")
        raise FirebaseIdentityError(503, "Sign-in service is temporarily unavailable.")

    @staticmethod
    def user(claims: dict) -> dict:
        uid = claims.get("uid") or claims.get("sub")
        if not isinstance(uid, str) or not 1 <= len(uid) <= 128:
            raise FirebaseIdentityError(401, "Your session is no longer valid. Sign in again.")
        guest = claims.get("firebase", {}).get("sign_in_provider") == "anonymous"
        email = claims.get("email", "")
        email = email if isinstance(email, str) else ""
        name = claims.get("name") or email.split("@")[0] or "Planner"
        return dict(
            id=uid,
            name="Demo planner" if guest else str(name)[:80],
            email=email,
            mode="guest" if guest else "firebase",
        )

    def _session(self, result: dict) -> tuple[str, dict, dict]:
        token = result.get("idToken")
        if not isinstance(token, str) or not token:
            raise FirebaseIdentityError(503, "Sign-in service returned no identity token.")
        try:
            claims = auth.verify_id_token(token, app=self.app, check_revoked=True)
            age = time.time() - float(claims.get("auth_time", 0))
            if not -30 <= age <= 300:
                raise FirebaseIdentityError(401, "Recent sign-in is required.")
            cookie = auth.create_session_cookie(
                token,
                expires_in=timedelta(hours=self.hours),
                app=self.app,
            )
        except FirebaseIdentityError:
            raise
        except (exceptions.FirebaseError, ValueError) as error:
            raise FirebaseIdentityError(
                503, "Could not create a secure session. Please retry."
            ) from error
        return cookie, self.user(claims), claims

    def register(self, name: str, email: str, password: str):
        result = self._request(
            "signUp", {"email": email, "password": password, "returnSecureToken": True}
        )
        uid = result.get("localId")
        try:
            updated = self._request(
                "update",
                {"idToken": result["idToken"], "displayName": name, "returnSecureToken": True},
            )
            return self._session({**result, **updated})
        except (FirebaseIdentityError, KeyError) as error:
            # A registration that cannot issue a session should not silently leave
            # a half-created account. A provider failure may still require retry.
            if uid:
                try:
                    self.delete_user(uid)
                except FirebaseIdentityError:
                    pass
            if isinstance(error, KeyError):
                raise FirebaseIdentityError(
                    503, "Sign-in service returned an invalid response."
                ) from error
            raise

    def login(self, email: str, password: str):
        return self._session(
            self._request(
                "signInWithPassword",
                {
                    "email": email,
                    "password": password,
                    "returnSecureToken": True,
                },
            )
        )

    def guest(self):
        result = self._request("signUp", {"returnSecureToken": True})
        try:
            return self._session(result)
        except FirebaseIdentityError:
            if result.get("localId"):
                try:
                    self.delete_user(result["localId"])
                except FirebaseIdentityError:
                    pass
            raise

    def verify(self, cookie: str | None) -> dict | None:
        if not cookie or len(cookie) > 12000:
            return None
        try:
            return auth.verify_session_cookie(cookie, check_revoked=True, app=self.app)
        except (
            auth.InvalidSessionCookieError,
            auth.ExpiredSessionCookieError,
            auth.RevokedSessionCookieError,
            auth.UserDisabledError,
            auth.UserNotFoundError,
            ValueError,
        ):
            return None
        except exceptions.FirebaseError as error:
            raise FirebaseIdentityError(
                503, "Session verification is temporarily unavailable."
            ) from error

    def reset_password(self, email: str):
        self._request("sendOobCode", {"requestType": "PASSWORD_RESET", "email": email}, reset=True)

    def disable_user(self, uid: str):
        try:
            auth.update_user(uid, disabled=True, app=self.app)
        except auth.UserNotFoundError:
            return
        except exceptions.FirebaseError as error:
            raise FirebaseIdentityError(
                503, "Account deletion could not be completed. Please retry."
            ) from error

    def delete_user(self, uid: str):
        try:
            auth.delete_user(uid, app=self.app)
        except auth.UserNotFoundError:
            return
        except exceptions.FirebaseError as error:
            raise FirebaseIdentityError(
                503, "Account deletion could not be completed. Please retry."
            ) from error
