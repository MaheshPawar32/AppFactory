#!/usr/bin/env python3
"""Safely orchestrate the existing Flutter build engine across registered apps."""
from __future__ import annotations
import argparse, csv, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "apps" / "PROJECT_REGISTRY.csv"
ENGINE = ROOT / "scripts" / "flutter_build_engine.py"

def load_apps(registry: Path, base: Path, names=None):
    if not registry.is_file():
        raise ValueError(f"Registry not found: {registry}")
    with registry.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("Registry has no header")
        rows = list(reader)
    selected=[]
    for row in rows:
        name=(row.get("app_name") or "").strip()
        if not name:
            continue
        if names and name not in names:
            continue
        raw=(row.get("project_path") or "").strip()
        path=Path(raw).expanduser() if raw else None
        if path and not path.is_absolute():
            path=(base/path).resolve()
        if not path:
            status="BLOCKED"; reason="project_path is empty in registry"
        elif not path.is_dir():
            status="BLOCKED"; reason=f"project path does not exist: {path}"
        elif not (path/"pubspec.yaml").is_file():
            status="BLOCKED"; reason=f"pubspec.yaml missing: {path}"
        else:
            status="READY"; reason="Flutter project manifest found"
        selected.append({"app_name":name,"package_name":(row.get("package_name") or "").strip(),
                         "project_path":str(path) if path else "", "preflight_status":status,
                         "reason":reason,"registry_row":row})
    unknown=set(names or [])-{a["app_name"] for a in selected}
    if unknown:
        raise ValueError("Unknown app name(s): "+", ".join(sorted(unknown)))
    return selected

def run_batch(apps, execute=False, build="none", skip_tests=False, fix_mode="none", max_retries=1, output_dir=None):
    results=[]
    for app in apps:
        item={k:v for k,v in app.items() if k!="registry_row"}
        item["settings"]={"build":build,"skip_tests":skip_tests,"fix_mode":fix_mode,"max_retries":max_retries}
        if app["preflight_status"]!="READY":
            item.update({"status":"BLOCKED","engine_report":None})
        elif not execute:
            item.update({"status":"DRY RUN","engine_report":None,
                         "planned_engine_command":[sys.executable,str(ENGINE),app["project_path"],
                            "--build",build,"--fix-mode",fix_mode,"--max-retries",str(max_retries),"--dry-run"]+
                            (["--skip-tests"] if skip_tests else [])})
        else:
            report_dir=(Path(output_dir).resolve()/safe_name(app["app_name"]) if output_dir else
                        Path(app["project_path"])/"build"/"factory_batch_runs"/safe_name(app["app_name"]))
            cmd=[sys.executable,str(ENGINE),app["project_path"],"--build",build,
                 "--fix-mode",fix_mode,"--max-retries",str(max_retries),"--run-dir",str(report_dir)]
            if skip_tests: cmd.append("--skip-tests")
            try:
                proc=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=3600)
                report_path=report_dir/"report.json"
                engine_report=None
                if report_path.is_file():
                    try: engine_report=json.loads(report_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError: pass
                status=(engine_report or {}).get("overall_status")
                if not status:
                    status="PASS" if proc.returncode==0 else ("BLOCKED" if proc.returncode==2 else "FAIL")
                item.update({"status":status,"engine_exit_code":proc.returncode,
                             "engine_report":str(report_path) if report_path.exists() else None,
                             "stdout_tail":proc.stdout[-1200:],"stderr_tail":proc.stderr[-1200:]})
            except subprocess.TimeoutExpired:
                item.update({"status":"BLOCKED","error":"Build engine exceeded 60-minute timeout"})
        results.append(item)
    counts={}
    for item in results: counts[item["status"]]=counts.get(item["status"],0)+1
    return {"schema_version":1,"generated_at":datetime.now(timezone.utc).isoformat(),
            "mode":"EXECUTE" if execute else "DRY RUN","settings":{"build":build,"skip_tests":skip_tests,
            "fix_mode":fix_mode,"max_retries":max_retries},"summary":{"selected":len(results),"statuses":counts},
            "apps":results,"safety_note":"No app source is generated and no app is published. Registry updates are never automatic."}

def safe_name(name):
    out="".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")
    return out or "app"

def update_registry(registry, results):
    with registry.open(newline="",encoding="utf-8-sig") as f:
        reader=csv.DictReader(f); fields=reader.fieldnames or []; rows=list(reader)
    if not fields: raise ValueError("Cannot update registry without header")
    now=datetime.now(timezone.utc).isoformat()
    by_name={x["app_name"]:x for x in results}
    for row in rows:
        result=by_name.get((row.get("app_name") or "").strip())
        if not result: continue
        status=result["status"]
        row["last_checked_at"]=now if "last_checked_at" in fields else row.get("last_checked_at","")
        if "last_analyzer_status" in fields:
            row["last_analyzer_status"] = status if status in ("PASS","FAIL","BLOCKED") else row.get("last_analyzer_status","NOT RUN")
        if "last_test_status" in fields and not result.get("settings",{}).get("skip_tests",False):
            row["last_test_status"] = status if status in ("PASS","FAIL","BLOCKED") else row.get("last_test_status","NOT RUN")
        if "last_build_status" in fields and result.get("settings",{}).get("build","none")!="none":
            row["last_build_status"] = status if status in ("PASS","FAIL","BLOCKED") else row.get("last_build_status","NOT RUN")
        if "evidence_path" in fields and result.get("engine_report"):
            row["evidence_path"]=result["engine_report"]
    tmp=registry.with_suffix(registry.suffix+".tmp")
    with tmp.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    tmp.replace(registry)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--registry",type=Path,default=REGISTRY)
    p.add_argument("--base",type=Path,default=ROOT)
    p.add_argument("--app",action="append",help="App name from registry; repeat to select multiple. Default: all registered apps")
    p.add_argument("--execute",action="store_true",help="Actually run the build engine. Default is dry-run.")
    p.add_argument("--build",choices=("none","apk","appbundle"),default="none",
                   help="Artifact build type; default none (quality checks only)")
    p.add_argument("--skip-tests",action="store_true")
    p.add_argument("--fix-mode",choices=("none","safe"),default="none",
                   help="Default none to avoid automatic formatting edits")
    p.add_argument("--max-retries",type=int,choices=(0,1,2),default=1)
    p.add_argument("--output",type=Path,default=ROOT/"reports"/"batch_build_report.json")
    p.add_argument("--run-output-dir",type=Path)
    p.add_argument("--update-registry",action="store_true",help="Explicitly write result statuses/evidence back to CSV")
    a=p.parse_args(argv)
    if a.update_registry and not a.execute:
        p.error("--update-registry requires --execute")
    try:
        apps=load_apps(a.registry,a.base.resolve(),a.app)
        report=run_batch(apps,a.execute,a.build,a.skip_tests,a.fix_mode,a.max_retries,a.run_output_dir)
        if a.update_registry:
            update_registry(a.registry,report["apps"])
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(report,indent=2))
    except (ValueError,OSError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr);return 1
    return 0 if all(x["status"] not in ("FAIL","BLOCKED") for x in report["apps"]) else 2

if __name__=="__main__":
    raise SystemExit(main())
