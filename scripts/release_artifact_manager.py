#!/usr/bin/env python3
"""Index build-engine reports and APK/AAB artifacts into a local release history."""
from __future__ import annotations
import argparse, hashlib, json, os, re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_HISTORY=ROOT/"reports"/"release_history.jsonl"
DEFAULT_INDEX=ROOT/"reports"/"release_artifact_index.json"

def sha256_file(path: Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def safe_read_json(path):
    try:
        value=json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value,dict) else None
    except (OSError,json.JSONDecodeError):
        return None

def artifact_record(path: Path, project: Path, report: dict | None, indexed_at: str):
    stat=path.stat()
    rel=None
    try: rel=str(path.resolve().relative_to(project.resolve()))
    except ValueError: rel=str(path.resolve())
    return {
        "path":str(path.resolve()),"project_relative_path":rel,"file_name":path.name,
        "artifact_type":"AAB" if path.suffix.lower()==".aab" else "APK",
        "size_bytes":stat.st_size,"modified_at_utc":datetime.fromtimestamp(stat.st_mtime,timezone.utc).isoformat(),
        "sha256":sha256_file(path),"build_run_id":(report or {}).get("run_id"),
        "build_status":(report or {}).get("overall_status","UNKNOWN"),
        "app_version":(report or {}).get("app_version"),"indexed_at_utc":indexed_at,
        "signature_status":"NOT CHECKED","publish_status":"NOT PUBLISHED"
    }

def discover(project: Path, report_dirs=None, scan_build=True):
    found_reports=[]
    for d in (report_dirs or []):
        d=Path(d)
        if d.is_file() and d.name=="report.json":
            found_reports.append(d)
        elif d.is_dir():
            found_reports.extend(d.rglob("report.json"))
    if scan_build and project.is_dir():
        # Restrict to factory run directories; avoid indexing arbitrary JSON files.
        for pattern in ("build/factory_runs/**/report.json","build/factory_batch_runs/**/report.json"):
            found_reports.extend(project.glob(pattern))
    report_map={}
    for rp in sorted(set(x.resolve() for x in found_reports)):
        data=safe_read_json(rp)
        if data:
            report_map[str(rp.parent.resolve())]=data
    artifact_paths=set()
    if project.is_dir():
        for pattern in ("build/app/outputs/flutter-apk/*.apk","build/app/outputs/bundle/**/*.aab"):
            artifact_paths.update(x.resolve() for x in project.glob(pattern) if x.is_file())
    records=[]
    now=datetime.now(timezone.utc).isoformat()
    for path in sorted(artifact_paths):
        parent_report=report_map.get(str(path.parent.resolve()))
        if parent_report is None:
            # Associate with newest discovered successful report only when path is under that run dir.
            for folder,data in report_map.items():
                try: path.relative_to(Path(folder))
                except ValueError: continue
                parent_report=data; break
        records.append(artifact_record(path,project,parent_report,now))
    return records, [{"report_path":k,"run_id":v.get("run_id"),"status":v.get("overall_status","UNKNOWN"),
                      "started_at_utc":v.get("started_at_utc"),"project":v.get("project")}
                     for k,v in sorted(report_map.items())]

def read_history(path):
    if not path.exists(): return []
    rows=[]
    for line_no,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
        if not line.strip(): continue
        try:
            item=json.loads(line)
            if isinstance(item,dict): rows.append(item)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSONL history at line {line_no}: {path}")
    return rows

def merge_history(existing, current):
    by_key={}
    for item in existing+current:
        key=item.get("sha256") or (item.get("path"),item.get("modified_at_utc"))
        by_key[key]=item
    return sorted(by_key.values(),key=lambda x:(x.get("indexed_at_utc",""),x.get("file_name","")))

def build_index(project, artifacts, reports, history):
    return {"schema_version":1,"generated_at_utc":datetime.now(timezone.utc).isoformat(),
            "project_path":str(project.resolve()),"summary":{"artifacts_found":len(artifacts),
            "apk_count":sum(a["artifact_type"]=="APK" for a in artifacts),
            "aab_count":sum(a["artifact_type"]=="AAB" for a in artifacts),
            "build_reports_found":len(reports),"history_records":len(history)},
            "artifacts":artifacts,"build_reports":reports,
            "history_note":"History records indexed artifact fingerprints; signing and publication are not verified."}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("project",type=Path,help="Flutter project root")
    p.add_argument("--report-dir",action="append",default=[],help="Additional engine report directory or report.json; repeatable")
    p.add_argument("--history",type=Path,default=DEFAULT_HISTORY)
    p.add_argument("--index",type=Path,default=DEFAULT_INDEX)
    p.add_argument("--no-build-scan",action="store_true",help="Do not scan standard Flutter artifact directories")
    p.add_argument("--record-history",action="store_true",help="Append newly indexed artifacts to the local history")
    p.add_argument("--json",action="store_true",help="Print the full index JSON")
    a=p.parse_args(argv)
    project=a.project.expanduser().resolve()
    if not project.is_dir() or not (project/"pubspec.yaml").is_file():
        print(json.dumps({"status":"BLOCKED","error":"Expected a Flutter project directory containing pubspec.yaml"}))
        return 2
    try:
        artifacts,reports=discover(project,a.report_dir,not a.no_build_scan)
        history=read_history(a.history)
        merged=merge_history(history,artifacts)
        index=build_index(project,artifacts,reports,merged)
        a.index.parent.mkdir(parents=True,exist_ok=True)
        a.index.write_text(json.dumps(index,indent=2)+"\n",encoding="utf-8")
        if a.record_history:
            a.history.parent.mkdir(parents=True,exist_ok=True)
            known={x.get("sha256") for x in history}
            with a.history.open("a",encoding="utf-8") as f:
                for item in artifacts:
                    if item["sha256"] not in known:
                        f.write(json.dumps(item,separators=(",",":"))+"\n")
        output=index if a.json else {"status":"PASS","index":str(a.index),"history":str(a.history),
            "summary":index["summary"],"record_history_enabled":a.record_history}
        print(json.dumps(output,indent=2))
        return 0
    except (OSError,ValueError) as exc:
        print(json.dumps({"status":"FAIL","error":str(exc)}),file=__import__("sys").stderr)
        return 1

if __name__=="__main__":
    raise SystemExit(main())
