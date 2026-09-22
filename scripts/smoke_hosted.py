"""Exercise a deployed release with disposable accounts and real persisted plans.

No password-reset email is sent. Credentials and cookies are never printed.
--retain-state writes a private, temporary credential file for a restart test;
--resume checks that account and plan after a rollout and then deletes both.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pypdf import PdfReader


def expect(response: httpx.Response, status: int = 200) -> httpx.Response:
    if response.status_code != status:
        # Do not dump request bodies, cookies or provider errors into test logs.
        raise AssertionError(f"{response.request.method} {response.request.url.path}: expected {status}, got {response.status_code}")
    return response


def authenticate(client: httpx.Client, endpoint: str, payload: dict, status: int = 200) -> dict:
    response = expect(client.post(endpoint, json=payload), status)
    data = response.json()
    assert data["auth_mode"] == "firebase"
    assert client.cookies.get("__session")
    cookie = response.headers["set-cookie"].lower()
    assert "secure" in cookie and "httponly" in cookie and "samesite=lax" in cookie
    assert "no-store" in response.headers.get("cache-control", "")
    client.headers["X-CSRF-Token"] = data["csrf_token"]
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="https://hawkerbridge-sg.web.app")
    parser.add_argument("--retain-state", type=Path)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--report", type=Path, default=Path("output/hosted-smoke.json"))
    args = parser.parse_args()
    if not args.url.startswith("https://") or (args.resume and args.retain_state):
        parser.error("Use HTTPS, and only one of --resume or --retain-state")
    headers = {"Origin": args.url, "User-Agent": "HawkerBridge-release-verification/1"}
    report = {"url": args.url, "verified_at": datetime.now(UTC).isoformat(), "checks": []}
    with httpx.Client(base_url=args.url, headers=headers, timeout=60) as owner, httpx.Client(base_url=args.url, headers=headers, timeout=60) as other:
        health = expect(owner.get("/api/health")).json()
        assert health["storage"] == "firestore" and health["auth_mode"] == "firebase"
        report["source_fingerprint"] = health["source_fingerprint"]
        for route in ("/", "/saved-plans"):
            assert "no-cache" in expect(owner.get(route)).headers.get("cache-control", "")
        report["checks"].append("HTML and SPA routes revalidate after releases")
        expect(owner.get("/api/plans"), 401)
        expect(owner.post("/api/auth/demo", json={}, headers={"Origin": "https://invalid.example"}), 403)
        report["checks"].append("Managed auth, durable storage, unauthenticated access and origin boundary")
        if args.resume:
            state = json.loads(args.resume.read_text())
            assert state["url"] == args.url
            authenticate(owner, "/api/auth/login", state["credentials"])
            plan = expect(owner.get(f'/api/plans/{state["plan_id"]}')).json()
            assert plan["title"] == state["title"] and plan["result"]["summary"]["total_meals"] == 225
            expect(owner.delete("/api/auth/account"), 204)
            args.resume.unlink()
            report["checks"].append("Account and saved plan survive container rollout; test account deleted")
        else:
            credentials = {"email": f"release-{secrets.token_hex(8)}@example.test", "password": secrets.token_urlsafe(30)}
            account_created = False
            retained = False
            try:
                authenticate(owner, "/api/auth/register", credentials | {"name": "Release verification"}, 201)
                account_created = True
                authenticate(other, "/api/auth/demo", {})
                expect(owner.post("/api/analyse", json={"date": "2026-09-28"}, headers={"X-CSRF-Token": "invalid"}), 403)
                parameters = {"date": "2026-09-28", "radius_m": 800, "budget": 1500}
                results = []
                for budget, meals, spent in [(1500, 225, 1500), (3000, 450, 2700), (6000, 450, 2700)]:
                    result = expect(owner.post("/api/optimise", json=parameters | {"budget": budget})).json()
                    assert result["summary"]["total_meals"] == meals
                    assert result["summary"]["spent"] == spent
                    results.append({"budget": budget, "planned_meals": meals, "spent": spent})
                report["budget_results"] = results
                report["checks"].append("225 / 450 / 450 capacity decision and CSRF protection")
                title = "Disposable hosted verification"
                plan = expect(owner.post("/api/plans", json={"title": title, "parameters": parameters, "notes": "Synthetic release test. No venue review or service dispatch."}), 201).json()
                pid = plan["id"]
                assert expect(other.get("/api/plans")).json()["plans"] == []
                for method in (other.get, other.delete):
                    expect(method(f"/api/plans/{pid}"), 404)
                expect(other.patch(f"/api/plans/{pid}", json={"title": "Not allowed", "expected_updated_at": plan["updated_at"]}), 404)
                expect(other.get(f"/api/plans/{pid}/export"), 404)
                expect(other.get("/api/brief", params={"plan_id": pid}), 404)
                report["checks"].append("Two-user read, update, delete, export and brief isolation")
                for kind in ("pdf", "csv", "json"):
                    export = expect(owner.get(f"/api/plans/{pid}/export", params={"format": kind}))
                    assert len(export.content) > 500
                    if kind == "pdf":
                        assert export.content.startswith(b"%PDF")
                        assert "225" in " ".join(p.extract_text() for p in PdfReader(io.BytesIO(export.content)).pages)
                    elif kind == "json":
                        assert export.json()["source_manifest"]["sources"]
                    else:
                        assert "Candidate locality" in export.text
                assert len(expect(owner.get("/api/brief", params={"plan_id": pid})).json()["sources"]) == 5
                evidence = expect(owner.get("/api/evidence")).json()
                assert evidence["evaluation_status"] == "current"
                assert evidence["workspace_execution"]["pipeline_result"] == "SUCCESS"
                assert evidence["workspace_execution"]["source_fingerprint"] == health["source_fingerprint"]
                assert len(evidence["workspace_execution"]["quality_checks"]) == 12
                assert evidence["cloud_evaluation"]["scenarios_evaluated"] == 9
                assert evidence["evaluation"]["summary"]["unique_runs"] == 15
                report["publication_id"] = evidence["workspace_execution"]["publication_id"]
                report["checks"].append("PDF text, CSV, preserved JSON, source brief and current evaluation")
                expect(owner.patch(f"/api/plans/{pid}", json={"notes": "Updated synthetic release note", "expected_updated_at": plan["updated_at"]}))
                expect(owner.patch(f"/api/plans/{pid}", json={"status": "reviewed", "expected_updated_at": plan["updated_at"]}), 409)
                report["checks"].append("A stale editor cannot overwrite newer notes or approve them")
                expect(owner.post("/api/auth/logout", json={}), 204)
                expect(owner.get("/api/plans"), 401)
                authenticate(owner, "/api/auth/login", credentials)
                assert expect(owner.get(f"/api/plans/{pid}")).json()["notes"] == "Updated synthetic release note"
                report["checks"].append("Sign out, revocation, sign in and saved-plan persistence")
                if args.retain_state:
                    args.retain_state.parent.mkdir(parents=True, exist_ok=True)
                    args.retain_state.write_text(json.dumps({"url": args.url, "credentials": credentials, "plan_id": pid, "title": title}))
                    os.chmod(args.retain_state, 0o600)
                    retained = True
                    report["checks"].append("Disposable account retained for explicit restart verification")
            finally:
                if other.cookies.get("__session"):
                    expect(other.delete("/api/auth/account"), 204)
                if account_created and not retained:
                    expect(owner.delete("/api/auth/account"), 204)
        report["passed"] = True
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
