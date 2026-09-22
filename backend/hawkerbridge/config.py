"""Explicit runtime configuration. Secrets are read only from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
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

    def validate(self):
        if self.auth_mode not in {"local", "databricks"} or self.storage not in {
            "local",
            "databricks",
        }:
            raise ValueError("Auth and storage mode must be local or databricks")
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
