#!/usr/bin/env python3
"""Multi-app control center: read project registry and produce an actionable JSON/HTML dashboard."""
from __future__ import annotations
import argparse, csv, html, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "apps" / "PROJECT_REGISTRY.csv"
VALID = {"PASS", "FAIL", "BLOCKED", "WARN", "NOT RUN", "UNKNOWN", "IN PROGRESS", "PLANNED"}

def load_registry(path):
    path = Path(path)
    if not path.is_file():
        return [], [f"Registry not found: {path}"]
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return [], ["Registry has no header"]
        rows = list(reader)
    return rows, []

def project_health(row, base):
    name = (row.get("app_name") or "").strip() or "Unnamed app"
    path_text = (row.get("project_path") or "").strip()
    project = Path(path_text).expanduser() if path_text else None
    if project and not project.is_absolute():
        project = (base / project).resolve()
    exists = bool(project and project.exists())
    statuses = {
        "analyzer": (row.get("last_analyzer_status") or "NOT RUN").strip().upper(),
        "tests": (row.get("last_test_status") or "NOT RUN").strip().upper(),
        "build": (row.get("last_build_status") or "NOT RUN").strip().upper(),
    }
    unknown = [k for k, v in statuses.items() if v not in VALID]
    if unknown:
        for k in unknown:
            statuses[k] = "UNKNOWN"
    if not path_text:
        health = "NEEDS_PATH"
        reason = "Set project_path in the registry."
    elif not exists:
        health = "MISSING_PATH"
        reason = "Project path does not exist; verify the path."
    elif any(v == "FAIL" for v in statuses.values()):
        health = "ATTENTION"
        reason = "One or more recorded checks failed."
    elif any(v in ("BLOCKED", "WARN") for v in statuses.values()):
        health = "REVIEW"
        reason = "Review blocked or warning statuses."
    elif any(v in ("NOT RUN", "UNKNOWN", "PLANNED", "IN PROGRESS") for v in statuses.values()):
        health = "NOT VERIFIED"
        reason = "Some checks are not verified yet."
    else:
        health = "RECORDED PASS"
        reason = "Registry records passing checks; rerun them after relevant changes."
    return {
        "app_name": name, "package_name": (row.get("package_name") or "").strip(),
        "project_path": path_text, "resolved_path": str(project) if project else None,
        "path_exists": exists, "version": (row.get("version") or "").strip(),
        "platform": (row.get("platform") or "android").strip(),
        "health": health, "reason": reason, "checks": statuses,
        "open_blockers": (row.get("open_blockers") or "").strip(),
        "next_action": (row.get("next_action") or "").strip(),
        "last_checked_at": (row.get("last_checked_at") or "").strip(),
        "evidence_path": (row.get("evidence_path") or "").strip(),
    }

def render_html(report):
    cards = []
    for app in report["apps"]:
        safe = lambda value: html.escape(str(value or "—"))
        cards.append(f"""
        <article class="card">
          <div class="top"><div><h2>{safe(app['app_name'])}</h2><p>{safe(app['package_name'])} · v{safe(app['version'])}</p></div>
          <span class="pill">{safe(app['health'])}</span></div>
          <p>{safe(app['reason'])}</p>
          <dl><dt>Analyzer</dt><dd>{safe(app['checks']['analyzer'])}</dd>
          <dt>Tests</dt><dd>{safe(app['checks']['tests'])}</dd>
          <dt>Build</dt><dd>{safe(app['checks']['build'])}</dd>
          <dt>Path</dt><dd class="path">{safe(app['project_path'])}</dd></dl>
          <p><b>Next action:</b> {safe(app['next_action'] or 'Review status and run required checks.')}</p>
          {('<p class="blocker"><b>Blocker:</b> ' + safe(app['open_blockers']) + '</p>') if app['open_blockers'] else ''}
        </article>""")
    content = "\n".join(cards) or '<p class="empty">No projects registered yet. Add your app to apps/PROJECT_REGISTRY.csv.</p>'
    warning_text = "\n".join(f"<li>{html.escape(w)}</li>" for w in report["warnings"])
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>MyAppFactory Control Center</title><style>
:root{{--bg:#f5f7fb;--panel:#fff;--ink:#172033;--muted:#64748b;--line:#e2e8f0;--accent:#5b4bdb}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}}
header{{padding:28px max(20px,calc((100vw - 1180px)/2));background:#17152b;color:white}}header h1{{margin:0 0 4px;font-size:clamp(24px,4vw,34px)}}header p{{margin:0;color:#c7c4e8}}
main{{max-width:1180px;margin:24px auto;padding:0 20px}}.stats{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:18px}}
.stat,.card,.warnings{{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:16px;box-shadow:0 4px 18px #17203308}}
.stat span{{display:block;color:var(--muted);font-size:13px}}.stat strong{{font-size:26px}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}}
.top{{display:flex;justify-content:space-between;gap:10px;align-items:start}}h2{{font-size:19px;margin:0}}.card p{{color:var(--muted);overflow-wrap:anywhere}}.pill{{font-size:11px;font-weight:700;padding:5px 8px;border-radius:999px;background:#eeeaff;color:#4537a8;white-space:nowrap}}
dl{{display:grid;grid-template-columns:100px 1fr;gap:6px;margin:16px 0}}dt{{color:var(--muted)}}dd{{margin:0;font-weight:600;overflow-wrap:anywhere}}.path{{font-size:12px;font-weight:400}}.blocker{{color:#b42318!important}}.warnings{{margin-bottom:18px}}.warnings h2{{margin-bottom:8px}}.empty{{padding:28px;background:white;border-radius:12px;color:var(--muted)}}
footer{{padding:24px 0;color:var(--muted);font-size:12px}}@media(max-width:720px){{.grid{{grid-template-columns:1fr}}.stats{{grid-template-columns:repeat(2,minmax(0,1fr))}}main{{margin:16px auto;padding:0 12px}}}}
</style></head><body><header><h1>MyAppFactory Control Center</h1><p>Multi-app status, blockers and next actions · Read-only report</p></header>
<main><section class="stats">
<div class="stat"><span>Registered apps</span><strong>{report['summary']['total']}</strong></div>
<div class="stat"><span>Need attention</span><strong>{report['summary']['attention']}</strong></div>
<div class="stat"><span>Not verified</span><strong>{report['summary']['not_verified']}</strong></div>
<div class="stat"><span>Missing paths</span><strong>{report['summary']['missing_paths']}</strong></div>
</section>{('<section class="warnings"><h2>Registry warnings</h2><ul>'+warning_text+'</ul></section>') if report['warnings'] else ''}
<section class="grid">{content}</section><footer>Generated {html.escape(report['generated_at'])}. Health reflects recorded registry values and path existence; this dashboard does not run builds or independently verify reported results.</footer></main></body></html>"""

def build_report(rows, base, warnings=None):
    apps = [project_health(row, base) for row in rows if (row.get("app_name") or "").strip()]
    summary = {
        "total": len(apps),
        "attention": sum(a["health"] == "ATTENTION" for a in apps),
        "not_verified": sum(a["health"] in ("NOT VERIFIED", "NEEDS_PATH", "REVIEW") for a in apps),
        "missing_paths": sum(a["health"] == "MISSING_PATH" for a in apps),
    }
    return {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary, "apps": apps, "warnings": warnings or []}

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    p.add_argument("--base", type=Path, default=ROOT, help="Base for relative project paths")
    p.add_argument("--json", action="store_true")
    p.add_argument("--html", type=Path, help="Write a standalone HTML dashboard")
    p.add_argument("--output", type=Path, help="Write JSON report to this path")
    a = p.parse_args(argv)
    rows, warnings = load_registry(a.registry)
    report = build_report(rows, a.base.resolve(), warnings)
    rendered = json.dumps(report, indent=2)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(rendered + "\n", encoding="utf-8")
    if a.html:
        a.html.parent.mkdir(parents=True, exist_ok=True)
        a.html.write_text(render_html(report), encoding="utf-8")
    if a.json or (not a.output and not a.html):
        print(rendered)
    else:
        print(f"Control center generated: {len(report['apps'])} apps; {report['summary']['attention']} need attention.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
