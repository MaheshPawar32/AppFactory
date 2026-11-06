#!/usr/bin/env python3
"""Combine registry status, build evidence, and artifact inventory into one release dashboard."""
from __future__ import annotations
import argparse, csv, hashlib, html, json, re
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
REGISTRY=ROOT/"apps"/"PROJECT_REGISTRY.csv"
VALID_EVIDENCE={"PASS","FAIL","BLOCKED","WARN","NOT RUN","UNKNOWN","DRY RUN"}

def read_registry(path):
    if not path.is_file(): raise ValueError(f"Registry not found: {path}")
    with path.open(newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames: raise ValueError("Registry has no header")
        return list(reader)

def load_json(path):
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data,dict) else None
    except (OSError,json.JSONDecodeError):
        return None

def latest_reports(project):
    found=[]
    if project.is_dir():
        for pattern in ("build/factory_runs/**/report.json","build/factory_batch_runs/**/report.json"):
            found.extend(project.glob(pattern))
    records=[]
    for path in sorted(set(found),key=lambda p:p.stat().st_mtime,reverse=True):
        data=load_json(path)
        if data:
            records.append({"path":str(path.resolve()),"mtime":path.stat().st_mtime,"data":data})
    return records

def _is_within(path, directory):
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False


def _project_path_matches(raw_path, project):
    if not isinstance(raw_path, str) or not raw_path.strip():
        return False
    try:
        return Path(raw_path).expanduser().resolve() == project.resolve()
    except (OSError, RuntimeError):
        return False


def _validate_artifact(record, project, index_path):
    if not isinstance(record, dict):
        return None, "artifact record is not an object"
    raw_path = record.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None, "artifact record has no path"

    raw_project = record.get("project_path")
    if raw_project is not None and not _project_path_matches(raw_project, project):
        return None, "artifact project_path does not match the registered project"

    artifact_path = Path(raw_path).expanduser()
    if not artifact_path.is_absolute():
        artifact_path = project / artifact_path
    try:
        artifact_path = artifact_path.resolve(strict=True)
        project = project.resolve(strict=True)
    except (OSError, RuntimeError):
        return None, "artifact path is missing or cannot be resolved"
    permitted_directories = (project / "build", project / "reports")
    if not any(_is_within(artifact_path, directory.resolve()) for directory in permitted_directories):
        return None, "artifact is outside this app's build/ and reports/ directories"
    if not artifact_path.is_file():
        return None, "artifact path is not a regular file"

    suffix_type = {".apk": "APK", ".aab": "AAB"}.get(artifact_path.suffix.lower())
    artifact_type = str(record.get("artifact_type", "")).upper()
    if suffix_type is None or (artifact_type and artifact_type != suffix_type):
        return None, "artifact type does not match its APK/AAB file extension"

    recorded_size = record.get("size_bytes")
    if recorded_size is None:
        return None, "artifact record has no indexed size"
    try:
        actual_size = artifact_path.stat().st_size
    except OSError:
        return None, "artifact metadata could not be read"
    if recorded_size is not None:
        if type(recorded_size) is not int or recorded_size != actual_size:
            return None, "artifact size does not match the indexed record"

    recorded_hash = record.get("sha256")
    if recorded_hash is None:
        return None, "artifact record has no SHA-256 integrity metadata"
    if not isinstance(recorded_hash, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", recorded_hash):
        return None, "artifact SHA-256 metadata is malformed"
    digest = hashlib.sha256()
    try:
        with artifact_path.open("rb") as artifact_file:
            for chunk in iter(lambda: artifact_file.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None, "artifact could not be read for checksum validation"
    if digest.hexdigest().lower() != recorded_hash.lower():
        return None, "artifact SHA-256 does not match the indexed record"

    relative_path = record.get("project_relative_path")
    if relative_path is not None:
        try:
            indexed_relative = Path(relative_path)
            actual_relative = artifact_path.relative_to(project)
        except (TypeError, ValueError):
            return None, "artifact project-relative path is malformed or outside the project"
        if indexed_relative.is_absolute() or indexed_relative != actual_relative:
            return None, "artifact project-relative path does not match its resolved path"

    validated = dict(record)
    validated["path"] = str(artifact_path)
    validated["artifact_type"] = suffix_type
    validated["project_relative_path"] = str(artifact_path.relative_to(project))
    validated["evidence_index"] = str(index_path)
    return validated, None


def artifact_index_for(row, project, base):
    raw=(row.get("evidence_path") or "").strip()
    project = project.resolve()
    base = base.resolve()
    candidates=[]
    if raw:
        p=Path(raw).expanduser()
        candidates.append(p if p.is_absolute() else (base/p).resolve())
    candidates.extend([
        project/"reports"/"release_artifact_index.json",
        base/"reports"/"release_artifact_index.json",
    ])
    issues=[]
    seen=set()
    for candidate in candidates:
        try:
            candidate=candidate.resolve(strict=True)
        except (OSError,RuntimeError):
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        if not candidate.is_file():
            continue
        local_index=_is_within(candidate, project/"reports")
        global_index=_is_within(candidate, base/"reports")
        if not (local_index or global_index):
            issues.append(f"Rejected artifact index outside permitted reports directories: {candidate}")
            continue
        data=load_json(candidate)
        if data is None:
            issues.append(f"Rejected missing or malformed artifact index: {candidate}")
            continue
        associated_path=data.get("project_path")
        if associated_path is not None:
            if not _project_path_matches(associated_path, project):
                issues.append(f"Rejected artifact index associated with another project: {candidate}")
                continue
        elif not local_index:
            issues.append(f"Rejected shared artifact index without matching project_path: {candidate}")
            continue

        artifact_records=data.get("artifacts", [])
        if not isinstance(artifact_records, list):
            issues.append(f"Rejected malformed artifacts list in index: {candidate}")
            continue
        validated=[]
        for record in artifact_records:
            artifact, problem=_validate_artifact(record, project, candidate)
            if problem:
                issues.append(f"Rejected artifact in {candidate}: {problem}")
            else:
                validated.append(artifact)
        return validated, str(candidate), issues
    return [], None, issues

def assess(row, base):
    name=(row.get("app_name") or "").strip() or "Unnamed app"
    raw=(row.get("project_path") or "").strip()
    project=Path(raw).expanduser() if raw else None
    if project and not project.is_absolute(): project=(base/project).resolve()
    exists=bool(project and project.is_dir())
    manifest=bool(exists and (project/"pubspec.yaml").is_file())
    registry_checks={key:(row.get(col) or "NOT RUN").strip().upper()
        for key,col in (("analyzer","last_analyzer_status"),("tests","last_test_status"),("build","last_build_status"))}
    registry_checks={k:(v if v in VALID_EVIDENCE else "UNKNOWN") for k,v in registry_checks.items()}
    reports=latest_reports(project) if manifest else []
    latest=reports[0]["data"] if reports else None
    real_artifacts,index_path,artifact_issues=artifact_index_for(row,project,base) if manifest else ([],None,[])
    latest_status=str((latest or {}).get("overall_status","UNKNOWN")).upper()
    if not raw or not exists or not manifest:
        release_status="BLOCKED"; reason="Project path or Flutter pubspec.yaml is missing."
    elif latest_status in ("FAIL","BLOCKED"):
        release_status="ATTENTION"; reason="Latest discovered build-engine report records a failure or blocker."
    elif latest_status=="PASS":
        if not real_artifacts:
            release_status="NEEDS ARTIFACT"; reason="Latest report passed, but no existing artifact in the selected index was verified on disk."
        else:
            release_status="REVIEW REQUIRED"; reason="Build evidence and artifact files exist; signing, installability and store compliance still require review."
    elif any(v=="FAIL" for v in registry_checks.values()):
        release_status="ATTENTION"; reason="Registry records a failed check; no newer passing report was found."
    else:
        release_status="NOT VERIFIED"; reason="Insufficient current build evidence for release readiness."
    return {
        "app_name":name,"package_name":(row.get("package_name") or "").strip(),
        "version":(row.get("version") or "").strip(),"project_path":str(project) if project else "",
        "project_exists":exists,"pubspec_exists":manifest,"release_status":release_status,"reason":reason,
        "registry_statuses":registry_checks,"latest_engine_report":{
            "path":str(reports[0]["path"]) if reports else None,
            "run_id":(latest or {}).get("run_id"),"status":latest_status,
            "started_at_utc":(latest or {}).get("started_at_utc"),
            "dry_run":(latest or {}).get("dry_run")} if latest else None,
        "build_reports_found":len(reports),"artifact_index_path":index_path,
        "artifact_evidence_warnings":artifact_issues,
        "artifacts":[{"file_name":a.get("file_name"),"type":a.get("artifact_type"),
            "size_bytes":a.get("size_bytes"),"sha256":a.get("sha256"),"path":a.get("path"),
            "signature_status":a.get("signature_status","NOT CHECKED"),
            "publish_status":a.get("publish_status","NOT PUBLISHED")} for a in real_artifacts],
        "next_action":(row.get("next_action") or "").strip(),
        "open_blockers":(row.get("open_blockers") or "").strip(),
        "evidence_note":"Registry values are recorded claims; engine reports are local evidence; artifact file existence is checked. Signing and store readiness are not verified."
    }

def build_dashboard(registry, base):
    rows=read_registry(registry)
    apps=[assess(row,base) for row in rows if (row.get("app_name") or "").strip()]
    counts={}
    for app in apps: counts[app["release_status"]]=counts.get(app["release_status"],0)+1
    return {"schema_version":1,"generated_at_utc":datetime.now(timezone.utc).isoformat(),
            "summary":{"apps":len(apps),"statuses":counts,
            "release_ready_count":0,"note":"No status means automatic permission to publish; human release review is required."},
            "apps":apps}

def render_html(report):
    esc=lambda v:html.escape(str(v if v not in (None,"") else "—"))
    cards=[]
    for app in report["apps"]:
        artifacts="".join(f"<li>{esc(a['file_name'])} · {esc(a['type'])} · {esc(a['size_bytes'])} bytes<br><small>SHA-256: {esc(a['sha256'])}</small><br><small>Signature: {esc(a['signature_status'])} · {esc(a['publish_status'])}</small></li>" for a in app["artifacts"]) or "<li>No indexed artifact found</li>"
        checks="".join(f"<span class='check'>{esc(k)}: {esc(v)}</span>" for k,v in app["registry_statuses"].items())
        cards.append(f"<article><header><div><h2>{esc(app['app_name'])}</h2><p>{esc(app['package_name'])} · v{esc(app['version'])}</p></div><b>{esc(app['release_status'])}</b></header><p>{esc(app['reason'])}</p><div>{checks}</div><p><strong>Latest engine report:</strong> {esc((app['latest_engine_report'] or {}).get('status','NONE FOUND'))} · {esc((app['latest_engine_report'] or {}).get('path'))}</p><ul>{artifacts}</ul><p><strong>Next action:</strong> {esc(app['next_action'])}</p><p><strong>Blockers:</strong> {esc(app['open_blockers'])}</p></article>")
    summary=report["summary"]
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MyAppFactory Release Readiness</title><style>
:root{{color-scheme:light dark;font-family:Inter,system-ui,sans-serif}}body{{margin:0;background:Canvas;color:CanvasText}}main{{max-width:1100px;margin:auto;padding:28px 18px}}.summary{{display:flex;gap:12px;flex-wrap:wrap}}.tile,article{{border:1px solid #8886;border-radius:16px;padding:16px}}.tile{{min-width:130px;flex:1}}article{{margin-top:14px}}header{{display:flex;justify-content:space-between;gap:12px;align-items:center}}h1{{font-size:clamp(24px,4vw,36px)}}h2{{margin:0}}p{{line-height:1.5}}.check{{display:inline-block;border:1px solid #8888;border-radius:999px;padding:5px 9px;margin:3px;font-size:12px}}small{{overflow-wrap:anywhere}}code{{overflow-wrap:anywhere}}footer{{opacity:.75;margin-top:24px}}</style><main><h1>Release readiness</h1><p>Evidence-led overview of registered Flutter projects. This dashboard does not authorize publishing.</p><section class="summary"><div class="tile"><strong>Registered apps</strong><h2>{summary['apps']}</h2></div>{''.join(f"<div class='tile'><strong>{esc(k)}</strong><h2>{v}</h2></div>" for k,v in sorted(summary['statuses'].items()))}</section>{''.join(cards)}<footer>Generated {esc(report['generated_at_utc'])}. Signing, installation, privacy, store policy and publication are not verified by this report.</footer></main></html>"""

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--registry",type=Path,default=REGISTRY)
    p.add_argument("--base",type=Path,default=ROOT)
    p.add_argument("--json",type=Path,help="Write JSON report to this path; prints to stdout if omitted")
    p.add_argument("--html",type=Path,help="Optional HTML report output path")
    a=p.parse_args(argv)
    try:
        report=build_dashboard(a.registry,a.base.resolve())
        payload=json.dumps(report,indent=2)+"\n"
        if a.json:
            a.json.parent.mkdir(parents=True,exist_ok=True);a.json.write_text(payload,encoding="utf-8")
        else: print(payload,end="")
        if a.html:
            a.html.parent.mkdir(parents=True,exist_ok=True);a.html.write_text(render_html(report),encoding="utf-8")
        return 0
    except (OSError,ValueError) as exc:
        print(json.dumps({"status":"FAIL","error":str(exc)}),file=sys.stderr);return 1

if __name__=="__main__": raise SystemExit(main())
