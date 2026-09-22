"""Same-origin application API, secure local sessions and workspace identity support."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import sqlite3
import threading
import time
import uuid
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import ROOT, Settings
from .engine import MODEL_VERSION, PlanningEngine
from .exports import plan_csv, plan_pdf
from .middleware import BodyLimitMiddleware
from .schemas import (
    AnalysisRequest,
    Credentials,
    OptimiseRequest,
    PlanCreate,
    PlanPatch,
    Registration,
)
from .store import LocalStore

logger = logging.getLogger("hawkerbridge")
COOKIE = "hb_session"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    settings.validate()
    app = FastAPI(
        title="HawkerBridge",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    local = LocalStore(settings.database_path) if settings.storage == "local" else None
    if settings.storage == "databricks":
        from .databricks_store import DatabricksStore

        store = DatabricksStore(settings)
        snapshot = store.load_snapshot()
    else:
        store = local
        snapshot = json.loads(settings.data_path.read_text())
    engine = PlanningEngine(snapshot)
    app.state.engine = engine
    app.state.store = store
    app.state.settings = settings
    solver_slots = threading.BoundedSemaphore(2)
    # Only used to bind CSRF tokens to a trusted platform identity. A restart refreshes the token.
    csrf_key = secrets.token_bytes(32)
    throttle_lock = threading.Lock()
    throttle: dict[str, list[float]] = {}

    def rate_limit(request: Request, key: str, limit: int = 12, seconds: int = 300):
        address = request.client.host if request.client else "unknown"
        key = hashlib.sha256(f"{key}:{address}".encode()).hexdigest()
        if local:
            allowed = local.rate_allowed(key, limit, seconds)
        else:
            now = time.monotonic()
            with throttle_lock:
                if len(throttle) > 10000:
                    for k in list(throttle):
                        if not throttle[k] or throttle[k][-1] < now - 3600:
                            del throttle[k]
                entries = [t for t in throttle.get(key, []) if t > now - seconds]
                allowed = len(entries) < limit
                if allowed:
                    entries.append(now)
                throttle[key] = entries
        if not allowed:
            raise HTTPException(
                429,
                "Too many requests. Please wait a few minutes.",
                headers={"Retry-After": str(seconds)},
            )

    def platform_user(request: Request) -> dict | None:
        # This mode is supported only behind the Databricks Apps proxy. Never enable
        # it on an internet-exposed standalone server, where headers are forgeable.
        identifier = request.headers.get("x-forwarded-user")
        email = request.headers.get("x-forwarded-email")
        if not identifier or not email:
            return None
        return dict(
            id=hashlib.sha256(identifier.encode()).hexdigest(),
            name=request.headers.get("x-forwarded-preferred-username") or email.split("@")[0],
            email=email,
            mode="databricks",
        )

    def session_info(request: Request) -> dict:
        if settings.auth_mode == "databricks":
            user = platform_user(request)
            csrf = (
                hmac.new(csrf_key, user["id"].encode(), hashlib.sha256).hexdigest()
                if user
                else None
            )
        else:
            found = local.session(request.cookies.get(COOKIE))
            csrf = found.pop("csrf") if found else None
            user = found
        return dict(user=user, csrf_token=csrf, auth_mode=settings.auth_mode)

    def require_user(request: Request) -> dict:
        info = session_info(request)
        if not info["user"]:
            raise HTTPException(401, "Sign in to your workspace to continue.")
        if request.method in {"POST", "PATCH", "DELETE", "PUT"}:
            supplied = request.headers.get("x-csrf-token", "")
            if not info["csrf_token"] or not hmac.compare_digest(supplied, info["csrf_token"]):
                raise HTTPException(403, "Your session token has changed. Refresh and try again.")
        return info["user"]

    def assert_local_auth():
        if settings.auth_mode != "local":
            raise HTTPException(403, "Use your Databricks workspace sign-in.")

    def new_login(request: Request, response: Response, user: dict):
        local.revoke(request.cookies.get(COOKIE))
        token, csrf = local.new_session(user["id"], settings.session_hours)
        response.set_cookie(
            COOKIE,
            token,
            httponly=True,
            secure=settings.secure_cookies,
            samesite="lax",
            max_age=settings.session_hours * 3600,
            path="/",
        )
        return dict(user=user, csrf_token=csrf, auth_mode=settings.auth_mode)

    def validate_year(parameters: dict):
        calendar_year = snapshot.get("manifest", {}).get("closures_year")
        if calendar_year and int(str(parameters["date"])[:4]) != int(calendar_year):
            raise HTTPException(
                422,
                f"This snapshot covers the {calendar_year} closure schedule. Choose a date in {calendar_year}.",
            )

    def analyse(parameters: dict):
        validate_year(parameters)
        try:
            return engine.analyse(parameters)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

    def optimise(parameters: dict):
        validate_year(parameters)
        if not solver_slots.acquire(blocking=False):
            raise HTTPException(
                429, "The planner is busy. Please retry shortly.", headers={"Retry-After": "5"}
            )
        try:
            return engine.optimise(parameters)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        finally:
            solver_slots.release()

    def owned_plan(user: dict, plan_id: str):
        plan = store.get_plan(user["id"], plan_id)
        if not plan:
            raise HTTPException(404, "Plan not found in this workspace.")
        return plan

    @app.middleware("http")
    async def security(request: Request, call_next):
        request_id = str(uuid.uuid4())
        if request.url.path.startswith("/api/") and request.method in {
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        }:
            # JSON plus origin checking blocks login CSRF before any session exists.
            origin = request.headers.get("origin")
            allowed = set(settings.allowed_origins)
            allowed.add(f"{request.url.scheme}://{request.url.netloc}")
            if settings.auth_mode == "databricks":
                forwarded = request.headers.get("x-forwarded-host", "")
                if forwarded and "/" not in forwarded and "," not in forwarded:
                    allowed.add("https://" + forwarded)
            if origin and origin not in allowed:
                return JSONResponse(
                    {"detail": "This request came from an untrusted origin."}, status_code=403
                )
            if request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse(
                    {"detail": "Cross-site requests are not allowed."}, status_code=403
                )
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Request failed id=%s path=%s", request_id, request.url.path)
            response = JSONResponse(
                {"detail": f"The request could not be completed. Reference {request_id}."},
                status_code=500,
            )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'"
        )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        if settings.secure_cookies:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.get("/api/health")
    def health():
        return dict(
            status="ready",
            version=MODEL_VERSION,
            storage=settings.storage,
            auth_mode=settings.auth_mode,
            snapshot_date=snapshot["manifest"].get("fetched_at"),
            source_fingerprint=engine.fingerprint,
        )

    @app.get("/api/auth/session")
    def session(request: Request):
        return session_info(request)

    @app.post("/api/auth/demo")
    def demo(request: Request, response: Response):
        assert_local_auth()
        rate_limit(request, "auth", limit=20)
        user = local.register("Demo planner", f"guest-{uuid.uuid4()}@demo.local", None, "guest")
        return new_login(request, response, user)

    @app.post("/api/auth/register", status_code=201)
    def register(body: Registration, request: Request, response: Response):
        assert_local_auth()
        rate_limit(request, "auth")
        try:
            user = local.register(body.name, body.email, body.password)
        except sqlite3.IntegrityError as error:
            raise HTTPException(
                409, "An account already uses that email. Try signing in."
            ) from error
        return new_login(request, response, user)

    @app.post("/api/auth/login")
    def login(body: Credentials, request: Request, response: Response):
        assert_local_auth()
        rate_limit(request, "auth")
        user = local.authenticate(body.email, body.password)
        if not user:
            raise HTTPException(401, "Email or password is incorrect.")
        return new_login(request, response, user)

    @app.post("/api/auth/logout", status_code=204)
    def logout(request: Request, response: Response, user: dict = Depends(require_user)):
        if local:
            local.revoke(request.cookies.get(COOKIE))
        response.delete_cookie(COOKIE, path="/")

    @app.delete("/api/auth/account", status_code=204)
    def delete_account(response: Response, user: dict = Depends(require_user)):
        assert_local_auth()
        local.delete_account(user["id"])
        response.delete_cookie(COOKIE, path="/")

    @app.get("/api/snapshot")
    def get_snapshot(user: dict = Depends(require_user)):
        return snapshot

    @app.post("/api/analyse")
    def analysis(body: AnalysisRequest, request: Request, user: dict = Depends(require_user)):
        rate_limit(request, "compute", limit=180, seconds=60)
        return analyse(body.model_dump(mode="json"))

    @app.post("/api/optimise")
    def optimization(body: OptimiseRequest, request: Request, user: dict = Depends(require_user)):
        rate_limit(request, "optimise", limit=60, seconds=60)
        return optimise(body.model_dump(mode="json"))

    @app.get("/api/plans")
    def list_plans(user: dict = Depends(require_user)):
        plans = store.list_plans(user["id"])
        return dict(
            plans=[
                {k: v for k, v in p.items() if k != "result"} | {"summary": p["result"]["summary"]}
                for p in plans
            ]
        )

    @app.post("/api/plans", status_code=201)
    def save_plan(body: PlanCreate, request: Request, user: dict = Depends(require_user)):
        rate_limit(request, "save", limit=30, seconds=60)
        if len(store.list_plans(user["id"])) >= 200:
            raise HTTPException(
                409, "This workspace has 200 plans. Remove an old plan before adding another."
            )
        params = body.parameters.model_dump(mode="json")
        result = optimise(params)
        now = datetime.now(UTC).isoformat()
        plan = dict(
            id=str(uuid.uuid4()),
            title=body.title,
            status="draft",
            created_at=now,
            updated_at=now,
            date=params["date"],
            parameters=params,
            result=result,
            notes=body.notes,
            source_manifest=deepcopy(snapshot["manifest"]),
            engine_code_sha256=hashlib.sha256(
                Path(__file__).with_name("engine.py").read_bytes()
            ).hexdigest(),
        )
        store.save_plan(user["id"], plan)
        return plan

    @app.get("/api/plans/{plan_id}")
    def get_plan(plan_id: str, user: dict = Depends(require_user)):
        return owned_plan(user, plan_id)

    @app.patch("/api/plans/{plan_id}")
    def update_plan(plan_id: str, body: PlanPatch, user: dict = Depends(require_user)):
        plan = owned_plan(user, plan_id)
        patch = body.model_dump(exclude_none=True)
        plan.update(patch)
        plan["updated_at"] = datetime.now(UTC).isoformat()
        if ("title" in patch or "notes" in patch) and "status" not in patch:
            plan["status"] = "draft"
            plan.pop("reviewed_at", None)
            plan.pop("reviewed_by", None)
        if patch.get("status") == "reviewed":
            plan["reviewed_at"] = plan["updated_at"]
            plan["reviewed_by"] = user["name"]
        elif patch.get("status") == "draft":
            plan.pop("reviewed_at", None)
            plan.pop("reviewed_by", None)
        store.save_plan(user["id"], plan)
        return plan

    @app.delete("/api/plans/{plan_id}", status_code=204)
    def delete_plan(plan_id: str, user: dict = Depends(require_user)):
        if not store.delete_plan(user["id"], plan_id):
            raise HTTPException(404, "Plan not found in this workspace.")

    @app.get("/api/plans/{plan_id}/export")
    def export(plan_id: str, format: str = "pdf", user: dict = Depends(require_user)):
        plan = owned_plan(user, plan_id)
        if format == "pdf":
            payload, mime = plan_pdf(plan), "application/pdf"
        elif format == "csv":
            payload, mime = plan_csv(plan), "text/csv; charset=utf-8"
        elif format == "json":
            payload, mime = (
                json.dumps(plan, indent=2, ensure_ascii=False, allow_nan=False).encode(),
                "application/json",
            )
        else:
            raise HTTPException(422, "Export format must be pdf, csv or json.")
        filename = f"hawkerbridge-{plan['date']}-{plan['id'][:8]}.{format}"
        return Response(
            payload,
            media_type=mime,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get("/api/brief")
    def brief(plan_id: str, user: dict = Depends(require_user)):
        plan = owned_plan(user, plan_id)
        return dict(
            title=plan["title"],
            text=plan["result"]["explanation"],
            method="Deterministic summary of computed plan; no language model",
            sources=plan.get("source_manifest", {}).get("sources", []),
            evidence_status="preserved"
            if plan.get("source_manifest")
            else "legacy_plan_missing_manifest",
        )

    @app.get("/api/evidence")
    def evidence(user: dict = Depends(require_user)):
        evaluation_status = "unavailable"
        if settings.storage == "databricks":
            from .databricks_store import DatabricksStoreError

            try:
                evaluation = store.load_evaluation(engine.fingerprint)
            except DatabricksStoreError:
                logger.warning("No complete Databricks evaluation for active snapshot")
                evaluation = None
        else:
            eval_path = ROOT / "data/processed/evaluation.json"
            evaluation = json.loads(eval_path.read_text()) if eval_path.exists() else None
        if evaluation:
            code_hash = hashlib.sha256(
                Path(__file__).with_name("engine.py").read_bytes()
            ).hexdigest()
            stale = evaluation.get("source_fingerprint") != engine.fingerprint
            stale |= bool(evaluation.get("engine_code_sha256") != code_hash)
            evaluation_status = "stale" if stale else "current"
            if stale:
                evaluation = None
        return dict(
            manifest=snapshot["manifest"],
            quarantine=snapshot.get("quarantine", []),
            food_waste=snapshot.get("food_waste", []),
            evaluation=evaluation,
            evaluation_status=evaluation_status,
            methodology=dict(
                version=MODEL_VERSION,
                spatial_unit="Census 2020 subzones",
                distance="Great-circle metres from a polygon representative point",
                exposure="A subzone is flagged if its representative point is within the chosen radius of any listed centre before closures but none during them.",
                demand="Ceiling of census subzone residents multiplied by a user-entered participation rate; an assumption, not a forecast.",
                objective="Maximise allocated meals weighted by 1 + (senior preference - 1) × subzone senior share.",
                constraints=[
                    "Daily setup and meal costs within budget",
                    "Each subzone demand counted once",
                    "Site capacity and maximum site count",
                    "Collection point within chosen straight-line reach",
                ],
                solver="Mixed-integer linear programming (SciPy/HiGHS); 5-second limit; verified feasible greedy fallback",
                baseline="Largest remaining demand first with the same budget, reach and capacities",
                limitations=engine.analyse(
                    {"date": f"{snapshot['manifest'].get('closures_year', 2026)}-09-22"}
                )["limitations"],
            ),
        )

    assets = settings.frontend_path / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "API endpoint not found")
        candidate = (settings.frontend_path / path).resolve()
        if candidate.is_relative_to(settings.frontend_path.resolve()) and candidate.is_file():
            return FileResponse(candidate)
        index = settings.frontend_path / "index.html"
        if not index.exists():
            return JSONResponse(
                {"detail": "Frontend is not built. Run npm ci && npm run build in frontend."},
                status_code=503,
            )
        return FileResponse(index)

    app.add_middleware(BodyLimitMiddleware, limit=65536)
    return app
