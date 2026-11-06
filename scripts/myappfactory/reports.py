"""Report vocabulary and per-app, refuse-overwrite report storage."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .redact import redact_obj

PASS, FAIL, PARTIAL = "PASS", "FAIL", "PARTIAL"
NOT_IMPLEMENTED, NOT_RUN, MANUAL = "NOT IMPLEMENTED", "NOT RUN", "NEEDS MANUAL VERIFICATION"
MILESTONE_STATUSES = (PASS, FAIL, PARTIAL, NOT_IMPLEMENTED, NOT_RUN, MANUAL)
# Check-level outcomes additionally allow these:
WARN, NOT_APPLICABLE, BLOCKED = "WARN", "NOT APPLICABLE", "BLOCKED"
CHECK_STATUSES = MILESTONE_STATUSES + (WARN, NOT_APPLICABLE, BLOCKED)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def check(name, status, detail="", **extra) -> dict:
    if status not in CHECK_STATUSES:
        raise ValueError(f"Invalid check status: {status}")
    return {"check": name, "status": status, "detail": detail, **extra}


def rollup(checks) -> str:
    """Overall status: any FAIL/BLOCKED -> FAIL; all PASS/NA -> PASS; else PARTIAL."""
    statuses = [c["status"] for c in checks]
    if not statuses:
        return NOT_RUN
    if any(s in (FAIL, BLOCKED) for s in statuses):
        return FAIL
    if all(s in (PASS, NOT_APPLICABLE) for s in statuses):
        return PASS
    if all(s in (NOT_RUN, NOT_APPLICABLE) for s in statuses):
        return NOT_RUN
    return PARTIAL


def make_report(app, kind, title, checks, *, milestone=None, data=None, limitations=(),
                manual=(), commands=(), status=None) -> dict:
    return {
        "schema_version": 1, "kind": kind, "title": title, "milestone": milestone,
        "generated_at": now(), "app": app.identity(),
        "status": status or rollup(checks), "checks": list(checks), "data": data or {},
        "commands": list(commands), "limitations": list(limitations),
        "manual_verification": list(manual),
    }


def write_report(app, report: dict, name=None) -> Path:
    """Write under state/apps/<id>/reports/<kind>/; never overwrite."""
    if report.get("app", {}).get("app_id") != app.app_id:
        raise PermissionError("Report app identity does not match the target app")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = app.state_path("reports", report["kind"], f"{name or stamp}.json")
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite report: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(redact_obj(report), indent=2), encoding="utf-8")
    return path


def list_reports(app, kind=None) -> list[Path]:
    base = app.state_path("reports")
    if not base.is_dir():
        return []
    pattern = f"{kind}/*.json" if kind else "*/*.json"
    return sorted(base.glob(pattern))


def latest_report(app, kind) -> dict | None:
    paths = list_reports(app, kind)
    if not paths:
        return None
    data = json.loads(paths[-1].read_text(encoding="utf-8"))
    if data.get("app", {}).get("app_id") != app.app_id:
        return None
    return data


def print_summary(report: dict, path=None):
    print(f"[{report['status']}] {report['title']} — {report['app']['app_id']}")
    for item in report["checks"]:
        print(f"  [{item['status']}] {item['check']}: {item['detail']}")
    if path:
        print(f"Report: {path}")
