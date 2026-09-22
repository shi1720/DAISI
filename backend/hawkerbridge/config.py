"""Explicit runtime configuration. Secrets are read only from the environment."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    evaluation_path: Path | None = field(
        default_factory=lambda: (
            Path(os.environ["HAWKERBRIDGE_EVALUATION"])
            if os.getenv("HAWKERBRIDGE_EVALUATION")
            else None
        )
    )
    databricks_evaluation_path: Path | None = field(
        default_factory=lambda: (
            Path(os.environ["HAWKERBRIDGE_DATABRICKS_EVALUATION"])
            if os.getenv("HAWKERBRIDGE_DATABRICKS_EVALUATION")
            else None
        )
    )
    databricks_publication_path: Path | None = field(
        default_factory=lambda: (
            Path(os.environ["HAWKERBRIDGE_DATABRICKS_PUBLICATION"])
            if os.getenv("HAWKERBRIDGE_DATABRICKS_PUBLICATION")
            else None
        )
    )
    data_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("HAWKERBRIDGE_SNAPSHOT", str(ROOT / "data/processed/snapshot.json"))
        )
    )
    database_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("HAWKERBRIDGE_DATABASE", str(ROOT / "state/hawkerbridge.db"))
        )
    )
    frontend_path: Path = field(default_factory=lambda: ROOT / "frontend/dist")
    auth_mode: str = field(default_factory=lambda: os.getenv("HAWKERBRIDGE_AUTH_MODE", "local"))
    storage: str = field(default_factory=lambda: os.getenv("HAWKERBRIDGE_STORAGE", "local"))
    secure_cookies: bool = field(
        default_factory=lambda: os.getenv("HAWKERBRIDGE_SECURE_COOKIES", "false").lower() == "true"
    )
    allowed_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            filter(
                None,
                os.getenv(
                    "HAWKERBRIDGE_ALLOWED_ORIGINS",
                    "http://localhost:8000,http://127.0.0.1:8000,http://localhost:5173,http://127.0.0.1:5173",
                ).split(","),
            )
        )
    )
    databricks_warehouse_id: str = field(
        default_factory=lambda: os.getenv("DATABRICKS_WAREHOUSE_ID", "")
    )
    catalog: str = field(default_factory=lambda: os.getenv("HAWKERBRIDGE_CATALOG", "workspace"))
    schema: str = field(default_factory=lambda: os.getenv("HAWKERBRIDGE_SCHEMA", "hawkerbridge"))
    session_hours: int = 12
    firebase_project: str = field(
        default_factory=lambda: os.getenv("HAWKERBRIDGE_FIREBASE_PROJECT", "")
    )
    firebase_api_key: str = field(
        default_factory=lambda: os.getenv("HAWKERBRIDGE_FIREBASE_API_KEY", ""), repr=False
    )
    firestore_database: str = field(
        default_factory=lambda: os.getenv("HAWKERBRIDGE_FIRESTORE_DATABASE", "(default)")
    )
    guest_retention_days: int = 7
    guest_plan_limit: int = 20
    plan_limit: int = 200
    auth_attempts_per_5_minutes: int = field(
        default_factory=lambda: int(os.getenv("HAWKERBRIDGE_AUTH_ATTEMPTS_PER_5_MINUTES", "120"))
    )
    guest_sessions_per_hour: int = field(
        default_factory=lambda: int(os.getenv("HAWKERBRIDGE_GUEST_SESSIONS_PER_HOUR", "120"))
    )
    password_resets_per_hour: int = field(
        default_factory=lambda: int(os.getenv("HAWKERBRIDGE_PASSWORD_RESETS_PER_HOUR", "30"))
    )

    def validate(self):
        if self.auth_mode not in {"local", "databricks", "firebase"} or self.storage not in {
            "local",
            "databricks",
            "firestore",
        }:
            raise ValueError("Unsupported auth or storage mode")
        if (self.auth_mode == "firebase") != (self.storage == "firestore"):
            raise ValueError("Firebase authentication requires Firestore storage and vice versa")
        if self.auth_mode == "firebase":
            if (
                not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", self.firebase_project)
                or not self.firebase_api_key
            ):
                raise ValueError("Firebase requires an explicit project and Web API key")
            if not self.secure_cookies or not self.allowed_origins:
                raise ValueError(
                    "Public hosting requires secure cookies and explicit HTTPS origins"
                )
            for origin in self.allowed_origins:
                parsed = urlsplit(origin)
                if (
                    parsed.scheme != "https"
                    or not parsed.hostname
                    or parsed.username
                    or parsed.password
                    or parsed.path
                    or parsed.query
                    or parsed.fragment
                    or "*" in origin
                ):
                    raise ValueError("Public hosting requires exact HTTPS origins without paths")
        if not 1 <= self.session_hours <= 120 or not 1 <= self.guest_retention_days <= 30:
            raise ValueError("Session and guest retention settings are outside safe bounds")
        if not 1 <= self.guest_plan_limit <= self.plan_limit <= 200:
            raise ValueError("Plan limits must be between 1 and 200")
        if not 10 <= self.auth_attempts_per_5_minutes <= 1000:
            raise ValueError("Global sign-in attempts must be between 10 and 1000 per five minutes")
        if not 5 <= self.guest_sessions_per_hour <= 1000:
            raise ValueError("Global guest sessions must be between 5 and 1000 per hour")
        if not 3 <= self.password_resets_per_hour <= 300:
            raise ValueError("Global password resets must be between 3 and 300 per hour")
        if os.getenv("K_SERVICE") and self.auth_mode == "local":
            raise ValueError("Cloud Run cannot use ephemeral local identity and storage")
        if self.auth_mode == "databricks" and self.storage != "databricks":
            raise ValueError("Databricks authentication requires durable Databricks storage")
        if self.auth_mode == "databricks" and not all(
            os.getenv(name)
            for name in (
                "DATABRICKS_APP_NAME",
                "DATABRICKS_APP_PORT",
                "DATABRICKS_WORKSPACE_ID",
                "DATABRICKS_HOST",
            )
        ):
            raise ValueError(
                "Workspace-header authentication requires the managed Databricks Apps runtime"
            )
        if self.storage == "databricks" and (
            self.auth_mode != "databricks" or not self.databricks_warehouse_id
        ):
            raise ValueError(
                "Databricks storage requires workspace auth and a SQL warehouse resource"
            )
