#!/usr/bin/env python3
"""Run configured Flutter UI tests and optionally capture emulator screenshots.

Screenshot capture is opt-in and uses adb. Test names and capture scenarios are
provided by a JSON manifest; this tool never guesses app UI selectors or taps
arbitrary coordinates. Captures require a running, unlocked Android device or
emulator and a manually prepared app state.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, json, re, shutil, subprocess, sys, time

def run_command(cmd, cwd, timeout=300):
    started=time.time()
    try:
        proc=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,timeout=timeout)
        return {"command":cmd,"exit_code":proc.returncode,
                "duration_seconds":round(time.time()-started,2),
                "stdout_tail":(proc.stdout or "").splitlines()[-25:],
                "stderr_tail":(proc.stderr or "").splitlines()[-25:],
                "status":"PASS" if proc.returncode==0 else "FAIL"}
    except subprocess.TimeoutExpired as exc:
        return {"command":cmd,"exit_code":None,"duration_seconds":round(time.time()-started,2),
                "stdout_tail":str(exc.stdout or "").splitlines()[-10:],
                "stderr_tail":str(exc.stderr or "").splitlines()[-10:],
                "status":"TIMEOUT"}
    except OSError as exc:
        return {"command":cmd,"exit_code":127,"duration_seconds":round(time.time()-started,2),
                "error":str(exc),"status":"BLOCKED"}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project",type=Path,help="Flutter project root")
    parser.add_argument("--manifest",type=Path,help="JSON manifest containing test commands and screenshot scenarios")
    parser.add_argument("--out",type=Path,help="Output directory (default: project/build/visual_qa/<timestamp>)")
    parser.add_argument("--run-tests",action="store_true",help="Run flutter test; integration tests are configured by manifest")
    parser.add_argument("--execute-manifest-commands",action="store_true",
                        help="Explicitly execute test_commands from the manifest")
    parser.add_argument("--capture",action="store_true",help="Capture screenshots from a connected Android device using adb")
    parser.add_argument("--device",help="adb device serial; required when multiple devices are connected")
    args=parser.parse_args()
    project=args.project.expanduser().resolve()
    run_id=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out=(args.out.expanduser().resolve() if args.out else project/"build"/"visual_qa"/run_id)
    report={"tool":"MyAppFactory Visual QA Runner","schema_version":1,"run_id":run_id,
            "project":str(project),"output_directory":str(out),"started_at_utc":datetime.now(timezone.utc).isoformat(),
            "tests":[],"captures":[],"manual_review_required":True,"overall_status":"NOT RUN",
            "manifest_commands_enabled":args.execute_manifest_commands,
            "note":"Screenshots and command results are evidence, not a guarantee of visual quality. Manual review remains required."}
    if not (project/"pubspec.yaml").is_file():
        report["overall_status"]="BLOCKED"; report["error"]="pubspec.yaml not found"
        print(json.dumps(report,indent=2)); return 2
    manifest={}
    if args.manifest:
        try:
            manifest=json.loads(args.manifest.expanduser().read_text(encoding="utf-8"))
            if not isinstance(manifest,dict): raise ValueError("manifest root must be an object")
        except (OSError,json.JSONDecodeError,ValueError) as exc:
            report["overall_status"]="BLOCKED"; report["error"]=f"Invalid manifest: {exc}"
            print(json.dumps(report,indent=2)); return 2
    out.mkdir(parents=True,exist_ok=True)
    if args.run_tests:
        report["tests"].append(run_command(["flutter","test"],project,timeout=600))
    test_commands=manifest.get("test_commands",[])
    if not isinstance(test_commands,list):
        report["tests"].append({"status":"BLOCKED","error":"test_commands must be an array"})
        test_commands=[]
    for test_cmd in test_commands:
        if not isinstance(test_cmd,list) or not test_cmd or not all(isinstance(x,str) for x in test_cmd):
            report["tests"].append({"status":"BLOCKED","error":"Each test_commands entry must be a non-empty array of strings"})
            continue
        if not args.execute_manifest_commands:
            report["tests"].append({"status":"NOT RUN","command":test_cmd,
                                    "reason":"Pass --execute-manifest-commands to run manifest commands"})
            continue
        # Do not use shell=True: command arrays avoid shell interpolation.
        report["tests"].append(run_command(test_cmd,project,timeout=900))
    if args.capture:
        adb=shutil.which("adb")
        if not adb:
            report["captures"].append({"status":"BLOCKED","reason":"adb not found on PATH"})
        else:
            devices=run_command([adb,"devices"],project,timeout=15)
            lines=devices.get("stdout_tail",[])
            connected=[line.split()[0] for line in lines if "\tdevice" in line]
            serial=args.device
            if serial and serial not in connected:
                report["captures"].append({"status":"BLOCKED","reason":"Requested device serial is not in adb devices list","device":serial})
            elif not serial and len(connected)!=1:
                report["captures"].append({"status":"BLOCKED","reason":"Exactly one connected device is required unless --device is specified","connected_devices":connected})
            else:
                serial=serial or connected[0]
                scenarios=manifest.get("screenshots",[])
                if not scenarios:
                    report["captures"].append({"status":"NOT RUN","reason":"Manifest has no screenshot scenarios; prepare each app screen/state manually"})
                for i,scenario in enumerate(scenarios,1):
                    if not isinstance(scenario,dict) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}",str(scenario.get("name",""))):
                        report["captures"].append({"status":"BLOCKED","reason":"Scenario must have a safe name containing letters, digits, underscore or hyphen","scenario_index":i})
                        continue
                    name=scenario["name"]
                    path=out/f"{i:02d}_{name}.png"
                    cmd=[adb]
                    if serial: cmd += ["-s",serial]
                    cmd += ["exec-out","screencap","-p"]
                    started=time.time()
                    try:
                        proc=subprocess.run(cmd,cwd=project,capture_output=True,timeout=20)
                        if proc.returncode==0 and proc.stdout.startswith(b"\x89PNG\r\n\x1a\n"):
                            path.write_bytes(proc.stdout)
                            report["captures"].append({"name":name,"status":"CAPTURED","device":serial,
                                "path":str(path),"size_bytes":path.stat().st_size,
                                "description":str(scenario.get("description","")),
                                "manual_review":"REQUIRED"})
                        else:
                            report["captures"].append({"name":name,"status":"FAIL","device":serial,
                                "exit_code":proc.returncode,"stderr":proc.stderr.decode(errors="replace")[-1000:]})
                    except (OSError,subprocess.TimeoutExpired) as exc:
                        report["captures"].append({"name":name,"status":"FAIL","device":serial,"error":str(exc)})
    report["finished_at_utc"]=datetime.now(timezone.utc).isoformat()
    test_failed=any(t.get("status") in ("FAIL","BLOCKED","TIMEOUT") for t in report["tests"])
    capture_failed=any(c.get("status") in ("FAIL","BLOCKED") for c in report["captures"])
    if test_failed or capture_failed: report["overall_status"]="FAIL"
    elif report["tests"] or any(c.get("status")=="CAPTURED" for c in report["captures"]): report["overall_status"]="EVIDENCE COLLECTED"
    else: report["overall_status"]="NOT RUN"
    (out/"visual_qa_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    return 1 if report["overall_status"]=="FAIL" else 0
if __name__=="__main__": sys.exit(main())
