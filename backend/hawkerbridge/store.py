"""SQLite persistence for a local single-process deployment.

No credentials are seeded. Passwords use Argon2id; cookies carry opaque, hashed tokens.
Databricks deployments use the workspace identity and Delta plan store instead.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

HASHER = PasswordHasher(time_cost=3, memory_cost=32768, parallelism=2)
DUMMY_HASH = HASHER.hash(secrets.token_urlsafe(32))


class LocalStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS users(
              id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
              password_hash TEXT, mode TEXT NOT NULL, created_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions(
              token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              csrf TEXT NOT NULL, expires_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS plans(
              id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
              plan_json TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS plans_owner ON plans(owner_id);
            CREATE TABLE IF NOT EXISTS throttle(key TEXT NOT NULL, at REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS throttle_key ON throttle(key, at);
            """)
        path.chmod(0o600)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def register(self, name: str, email: str, password: str | None, mode="local") -> dict:
        user = dict(id=str(uuid.uuid4()), name=name, email=email.lower(), mode=mode)
        hashed = HASHER.hash(password) if password else None
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO users VALUES(?,?,?,?,?,?)",
                (user["id"], name, email.lower(), hashed, mode, time.time()),
            )
        return user

    def authenticate(self, email: str, password: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email=? AND mode='local'", (email.lower(),)
            ).fetchone()
        try:
            ok = HASHER.verify(row["password_hash"] if row else DUMMY_HASH, password)
        except (VerificationError, InvalidHashError):
            return None
        if not ok or not row:
            return None
        if HASHER.check_needs_rehash(row["password_hash"]):
            with self.connect() as conn:
                conn.execute(
                    "UPDATE users SET password_hash=? WHERE id=?",
                    (HASHER.hash(password), row["id"]),
                )
        return {k: row[k] for k in ("id", "name", "email", "mode")}

    def new_session(self, user_id: str, hours: int) -> tuple[str, str]:
        token, csrf = secrets.token_urlsafe(40), secrets.token_urlsafe(32)
        with self.connect() as conn:
            conn.execute("DELETE FROM sessions WHERE expires_at < ?", (time.time(),))
            conn.execute(
                "INSERT INTO sessions VALUES(?,?,?,?)",
                (self.token_hash(token), user_id, csrf, time.time() + hours * 3600),
            )
        return token, csrf

    @staticmethod
    def token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def session(self, token: str | None) -> dict | None:
        if not token:
            return None
        with self.connect() as conn:
            row = conn.execute(
                """SELECT u.id,u.name,u.email,u.mode,s.csrf FROM sessions s
                JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?""",
                (self.token_hash(token), time.time()),
            ).fetchone()
        return dict(row) if row else None

    def revoke(self, token: str | None):
        if token:
            with self.connect() as conn:
                conn.execute("DELETE FROM sessions WHERE token_hash=?", (self.token_hash(token),))

    def rate_allowed(self, key: str, limit: int = 10, seconds: int = 300) -> bool:
        now = time.time()
        with self.connect() as conn:
            # Serialize count + insert so concurrent attempts cannot bypass the bucket.
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("DELETE FROM throttle WHERE at < ?", (now - max(seconds, 3600),))
            count = conn.execute(
                "SELECT COUNT(*) FROM throttle WHERE key=? AND at>?", (key, now - seconds)
            ).fetchone()[0]
            if count >= limit:
                return False
            conn.execute("INSERT INTO throttle VALUES(?,?)", (key, now))
        return True

    def list_plans(self, owner_id: str) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT plan_json FROM plans WHERE owner_id=? ORDER BY updated_at DESC LIMIT 200",
                (owner_id,),
            ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def get_plan(self, owner_id: str, plan_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT plan_json FROM plans WHERE owner_id=? AND id=?", (owner_id, plan_id)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def save_plan(self, owner_id: str, plan: dict):
        with self.connect() as conn:
            # The owner is included in the conflict predicate: ids cannot overwrite another account.
            conn.execute(
                """INSERT INTO plans VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE
                SET plan_json=excluded.plan_json, updated_at=excluded.updated_at WHERE plans.owner_id=excluded.owner_id""",
                (plan["id"], owner_id, json.dumps(plan), plan["updated_at"]),
            )

    def delete_plan(self, owner_id: str, plan_id: str) -> bool:
        with self.connect() as conn:
            cursor = conn.execute(
                "DELETE FROM plans WHERE owner_id=? AND id=?", (owner_id, plan_id)
            )
            return cursor.rowcount > 0

    def delete_account(self, owner_id: str):
        with self.connect() as conn:
            conn.execute("DELETE FROM users WHERE id=?", (owner_id,))
