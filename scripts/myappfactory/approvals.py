"""Human approval gates.

Tools call `require(action, payload)`. If no matching approval exists, a pending
request is recorded and ApprovalRequired is raised. A human approves it with a
separate explicit command (`factory.py approvals approve <id> --by <name>`).
Approvals are bound to the exact payload hash, expire, and are single-use, so an
approval for one artifact, migration or upload cannot authorise another.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .audit import AuditLog
from .redact import redact_obj

SENSITIVE_ACTIONS = {
    "delete_project": "Delete a project or files",
    "overwrite_app": "Overwrite an existing app",
    "major_dependency_upgrade": "Apply a major dependency upgrade",
    "database_migration": "Execute a database migration",
    "signing_operation": "Use release signing credentials",
    "production_build": "Build a production artifact with credentials",
    "play_upload": "Upload to Google Play Console",
    "production_rollout": "Start or increase a production rollout",
    "production_rollback": "Roll back a production release",
    "ai_code_modification": "Apply AI-generated source changes",
    "privacy_declaration": "Sign off privacy / Data Safety declarations",
    "device_data_restore": "Overwrite app data on a device",
    "production_release_approval": "Approve a production release",
    "feature_flag_production": "Change a production feature flag",
    "maintenance_execution": "Execute an approved maintenance task",
    "factory_change": "Change factory core configuration or templates",
    "external_ai_call": "Send project context to an external AI provider",
}
DEFAULT_TTL_HOURS = 24


class ApprovalRequired(PermissionError):
    def __init__(self, request: dict):
        self.request = request
        super().__init__(
            f"Approval required for '{request['action']}' (request {request['id']}). "
            f"Approve with: python3 scripts/factory.py approvals approve {request['id']} "
            f"--app {request['scope']} --by <your-name>")


class ApprovalError(ValueError):
    pass


def payload_hash(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def _now():
    return datetime.now(timezone.utc)


class ApprovalStore:
    def __init__(self, directory: Path, scope: str, audit: AuditLog | None = None):
        self.directory = Path(directory)
        self.scope = scope
        self.path = self.directory / "approvals.json"
        self.audit = audit or AuditLog(self.directory / "audit.log.jsonl")

    @classmethod
    def for_app(cls, app):
        return cls(app.state_dir, app.app_id)

    def _load(self) -> list[dict]:
        if not self.path.is_file():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, items):
        self.directory.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(items, indent=2), encoding="utf-8")
        temp.replace(self.path)

    def list(self, status=None) -> list[dict]:
        items = self._load()
        changed = False
        for item in items:
            if item["status"] in ("PENDING", "APPROVED") and datetime.fromisoformat(item["expires_at"]) < _now():
                item["status"] = "EXPIRED"
                changed = True
        if changed:
            self._save(items)
        return [i for i in items if status is None or i["status"] == status]

    def get(self, request_id) -> dict:
        for item in self.list():
            if item["id"] == request_id:
                return item
        raise ApprovalError(f"No approval request {request_id} in scope {self.scope}")

    def request(self, action, payload, reason="", requested_by="factory", ttl_hours=DEFAULT_TTL_HOURS) -> dict:
        if action not in SENSITIVE_ACTIONS:
            raise ApprovalError(f"Unknown sensitive action: {action}")
        digest = payload_hash(payload)
        items = self.list()
        for item in items:
            if item["action"] == action and item["payload_hash"] == digest and item["status"] == "PENDING":
                return item
        created = _now()
        item = {"id": f"apr_{secrets.token_hex(6)}", "scope": self.scope, "action": action,
                "description": SENSITIVE_ACTIONS[action], "payload_hash": digest,
                "payload_summary": redact_obj(payload), "reason": reason,
                "requested_by": requested_by, "requested_at": created.isoformat(),
                "expires_at": (created + timedelta(hours=ttl_hours)).isoformat(),
                "status": "PENDING", "decided_by": None, "decided_at": None,
                "decision_note": "", "consumed_at": None}
        items.append(item)
        self._save(items)
        self.audit.append("approval_requested", requested_by,
                          {"id": item["id"], "action": action, "reason": reason}, self.scope)
        return item

    def decide(self, request_id, approver, approve: bool, note="") -> dict:
        approver = (approver or "").strip()
        if not approver or approver.lower() in {"factory", "ai", "agent", "system", "auto"}:
            raise ApprovalError("A named human approver is required")
        items = self.list()
        for item in items:
            if item["id"] == request_id:
                if item["status"] != "PENDING":
                    raise ApprovalError(f"Request {request_id} is {item['status']}, not PENDING")
                item.update(status="APPROVED" if approve else "DENIED", decided_by=approver,
                            decided_at=_now().isoformat(), decision_note=note)
                self._save(items)
                self.audit.append("approval_" + ("granted" if approve else "denied"), approver,
                                  {"id": request_id, "action": item["action"], "note": note}, self.scope)
                return item
        raise ApprovalError(f"No approval request {request_id} in scope {self.scope}")

    def require(self, action, payload, reason="", requested_by="factory") -> dict:
        """Consume a matching approval or raise ApprovalRequired with a new pending request."""
        digest = payload_hash(payload)
        items = self.list()
        for item in items:
            if item["action"] == action and item["payload_hash"] == digest and item["status"] == "APPROVED":
                item.update(status="CONSUMED", consumed_at=_now().isoformat())
                self._save(items)
                self.audit.append("approval_consumed", requested_by,
                                  {"id": item["id"], "action": action}, self.scope)
                return item
        raise ApprovalRequired(self.request(action, payload, reason, requested_by))
