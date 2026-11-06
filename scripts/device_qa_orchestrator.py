#!/usr/bin/env python3
"""Registry-driven Flutter regression/device QA orchestrator; does not auto-navigate screens."""
from __future__ import annotations
import argparse, csv, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY=ROOT/"apps"/"PROJECT_REGISTRY.csv"
RUNNER=ROOT/"scripts"/"visual_qa_runner.py"

def load_projects(registry, base, names=None):
    with Path(registry).open(newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames: raise ValueError("Registry has no header")
        rows=list(reader)
    projects=[]
    for row in rows:
        name=(row.get("app_name") or "").strip()
        if not name or (names and name not in names): continue
        raw=(row.get("project_path") or "").strip()
        project=Path(raw).expanduser() if raw else None
        if project and not project.is_absolute(): project=(base/project).resolve()
        if not project or not project.is_dir() or not (project/"pubspec.yaml").is_file():
            status="BLOCKED"; reason="Project path or pubspec.yaml is missing"
        else:
            status="READY"; reason="Flutter project manifest found"
        projects.append({"app_name":name,"package_name":(row.get("package_name") or "").strip(),
                         "project_path":str(project) if project else "","preflight_status":status,"reason":reason})
    missing=set(names or [])-{x["app_name"] for x in projects}
    if missing: raise ValueError("Unknown app name(s): "+", ".join(sorted(missing)))
    return projects

def run_projects(projects, execute=False, run_tests=True, capture=False, device=None, manifest=None,
                 output_root=None, execute_manifest_commands=False):
    results=[]
    for app in projects:
        item=dict(app)
        item["mode"]="EXECUTE" if execute else "DRY RUN"
        if app["preflight_status"]!="READY":
            item["status"]="BLOCKED"; results.append(item); continue
        out=(Path(output_root).resolve()/safe_name(app["app_name"]) if output_root else
             Path(app["project_path"])/"build"/"factory_device_qa"/safe_name(app["app_name"]))
        cmd=[sys.executable,str(RUNNER),app["project_path"],"--out",str(out)]
        if manifest: cmd += ["--manifest",str(Path(manifest).expanduser().resolve())]
        if run_tests: cmd.append("--run-tests")
        if execute_manifest_commands: cmd.append("--execute-manifest-commands")
        if capture: cmd.append("--capture")
        if device: cmd += ["--device",device]
        item["planned_command"]=cmd
        if not execute:
            item["status"]="DRY RUN"
        else:
            try:
                proc=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=1200)
                report_path=out/"visual_qa_report.json"
                qa=None
                if report_path.is_file():
                    try: qa=json.loads(report_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError: pass
                if qa:
                    item["status"]=qa.get("overall_status","UNKNOWN")
                    item["qa_report_path"]=str(report_path)
                    item["qa_summary"]={"tests":qa.get("tests",[]),"captures":qa.get("captures",[]),
                                        "manual_review_required":qa.get("manual_review_required",True)}
                else:
                    item["status"]="BLOCKED" if proc.returncode==2 else "FAIL"
                    item["error"]="QA runner did not produce a readable report"
                item["exit_code"]=proc.returncode
                item["stdout_tail"]=proc.stdout[-1000:]; item["stderr_tail"]=proc.stderr[-1000:]
            except subprocess.TimeoutExpired:
                item["status"]="TIMEOUT"; item["error"]="QA run exceeded 20-minute timeout"
        results.append(item)
    counts={}
    for r in results: counts[r["status"]]=counts.get(r["status"],0)+1
    return {"schema_version":1,"generated_at_utc":datetime.now(timezone.utc).isoformat(),
            "mode":"EXECUTE" if execute else "DRY RUN","summary":{"selected":len(results),"statuses":counts},
            "apps":results,"safety_note":"No app navigation is automated. Screens must be prepared manually. Review screenshots and test evidence; no release is authorized by this report."}

def safe_name(value):
    return re.sub(r"[^a-z0-9_-]+","-",value.lower()).strip("-") or "app"

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--registry",type=Path,default=DEFAULT_REGISTRY)
    p.add_argument("--base",type=Path,default=ROOT)
    p.add_argument("--app",action="append",help="Registered app name; repeat to select multiple")
    p.add_argument("--execute",action="store_true",help="Actually run QA; default is dry-run")
    p.add_argument("--skip-tests",action="store_true")
    p.add_argument("--execute-manifest-commands",action="store_true",
                   help="Explicitly execute test_commands in the selected QA manifest")
    p.add_argument("--capture",action="store_true",help="Capture screens from connected Android device(s); prepare UI states manually")
    p.add_argument("--device",help="adb serial, required if multiple devices are connected")
    p.add_argument("--manifest",type=Path,help="Optional Visual QA JSON manifest")
    p.add_argument("--output-root",type=Path,default=ROOT/"reports"/"device_qa_runs")
    p.add_argument("--output",type=Path,default=ROOT/"reports"/"device_qa_summary.json")
    a=p.parse_args(argv)
    if a.device and not a.capture: p.error("--device requires --capture")
    try:
        apps=load_projects(a.registry,a.base.resolve(),a.app)
        report=run_projects(apps,a.execute,not a.skip_tests,a.capture,a.device,a.manifest,
                            a.output_root,a.execute_manifest_commands)
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(report,indent=2))
        return 0 if all(x["status"] not in ("FAIL","BLOCKED","TIMEOUT") for x in report["apps"]) else 2
    except (ValueError,OSError) as exc:
        print(json.dumps({"status":"FAIL","error":str(exc)},indent=2),file=sys.stderr);return 1

if __name__=="__main__": raise SystemExit(main())
