"""Append-only, hash-chained audit logs (tamper-evident, not tamper-proof)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .redact import redact_obj

GENESIS = "0" * 64


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(entry: dict) -> str:
    body = {k: v for k, v in entry.items() if k != "hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()


class AuditLog:
    def __init__(self, path: Path):
        self.path = Path(path)

    def entries(self) -> list[dict]:
        if not self.path.is_file():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def append(self, event: str, actor: str, details: dict | None = None, app_id: str | None = None) -> dict:
        existing = self.entries()
        entry = {"seq": len(existing) + 1, "at": now(), "event": event, "actor": actor,
                 "app_id": app_id, "details": redact_obj(details or {}),
                 "prev": existing[-1]["hash"] if existing else GENESIS}
        entry["hash"] = _digest(entry)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
        return entry

    def verify(self) -> tuple[bool, int | None]:
        """Return (ok, first_bad_seq)."""
        previous = GENESIS
        for entry in self.entries():
            if entry.get("prev") != previous or entry.get("hash") != _digest(entry):
                return False, entry.get("seq")
            previous = entry["hash"]
        return True, None


def app_audit(app) -> AuditLog:
    return AuditLog(app.state_path("audit.log.jsonl"))


def factory_audit(state_root: Path) -> AuditLog:
    return AuditLog(Path(state_root) / "factory" / "audit.log.jsonl")
