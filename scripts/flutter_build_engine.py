#!/usr/bin/env python3
"""Run a bounded, logged Flutter quality/build pipeline with conservative recovery.

This tool does not generate application code, edit Dart to fix analyzer/test errors,
delete user files, change signing, or publish anything. Safe recovery only applies
Dart formatting, retries dependency resolution once, and retries a failed build once
after dependency resolution. Use --dry-run to inspect planned commands.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

def command_version(command):
    executable = shutil.which(command[0])
    if not executable:
        return {"available": False, "path": None, "version": None}
    try:
        proc = subprocess.run([executable, *command[1:]], capture_output=True, text=True, timeout=12)
        output = (proc.stdout or proc.stderr).strip().splitlines()
        return {"available": True, "path": executable, "version": output[0] if output else "unknown",
                "exit_code": proc.returncode}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": True, "path": executable, "version": None, "error": str(exc)}

def git_snapshot(project):
    if not shutil.which("git") or not (project / ".git").exists():
        return {"available": False, "status": "NOT RUN", "detail": "Git executable or .git directory not found"}
    try:
        proc = subprocess.run(["git", "status", "--short"], cwd=project, capture_output=True,
                              text=True, timeout=10)
        return {"available": True, "status": "OK" if proc.returncode == 0 else "ERROR",
                "exit_code": proc.returncode, "working_tree": proc.stdout.splitlines(),
                "detail": "Read-only working-tree snapshot; no commit or stash performed"}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": True, "status": "ERROR", "detail": str(exc)}

def classify_failure(output):
    s = output.lower()
    patterns = [
        ("SDK_OR_TOOLCHAIN", ("flutter: command not found", "not recognized as an internal", "android sdk", "cmdline-tools", "licenses not accepted", "java version")),
        ("DEPENDENCY_RESOLUTION", ("version solving failed", "pub get failed", "because every version", "could not resolve")),
        ("DART_FORMAT", ("dart format", "formatted", "formatting issues")),
        ("ANALYZER", ("error •", "flutter analyze", "issues found")),
        ("TEST_FAILURE", ("some tests failed", "exception caught by test", "test failed", "flutter test")),
        ("ANDROID_BUILD", ("gradle", "assembleRelease".lower(), "bundleRelease".lower(), "flutter build")),
    ]
    for category, terms in patterns:
        if any(term in s for term in terms):
            return category
    return "UNKNOWN"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", type=Path, default=Path.cwd(), help="Flutter project root")
    parser.add_argument("--build", choices=("apk", "appbundle", "none"), default="apk",
                        help="Release artifact to build (default: apk)")
    parser.add_argument("--flavor", help="Optional Android product flavor for the artifact build")
    parser.add_argument("--dart-define", action="append", default=[], metavar="KEY=VALUE",
                        help="Compile-time Dart define for the artifact build; repeatable")
    parser.add_argument("--skip-tests", action="store_true", help="Skip flutter test")
    parser.add_argument("--fix-mode", choices=("none", "safe"), default="safe",
                        help="safe: run dart format . if format check fails; no code fixes for analyzer/test errors")
    parser.add_argument("--max-retries", type=int, choices=(0, 1, 2), default=1,
                        help="Bounded retry budget per eligible step (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without running Flutter commands")
    parser.add_argument("--run-dir", type=Path, default=None, help="Optional report/log directory")
    args = parser.parse_args()
    project = args.project.expanduser().resolve()
    if args.flavor and not re.fullmatch(r"[a-z][a-z0-9_-]*", args.flavor):
        parser.error("--flavor must start with a lowercase letter and contain only lowercase letters, digits, _ or -")
    for define in args.dart_define:
        key, separator, _value = define.partition("=")
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            parser.error("--dart-define values must use KEY=VALUE with a valid identifier key")
    if args.max_retries < 0:
        parser.error("--max-retries must be non-negative")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = (args.run_dir.expanduser().resolve() if args.run_dir else project / "build" / "factory_runs" / run_id)
    report = {
        "tool": "MyAppFactory Flutter Build Engine",
        "schema_version": 1,
        "run_id": run_id,
        "project": str(project),
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "settings": {"build": args.build, "skip_tests": args.skip_tests,
                     "fix_mode": args.fix_mode, "max_retries": args.max_retries,
                     "flavor": args.flavor, "dart_defines": args.dart_define},
        "environment": {},
        "git_before": git_snapshot(project),
        "steps": [],
        "recovery_actions": [],
        "artifact": None,
        "overall_status": "NOT RUN",
        "limitations": [
            "No app source is generated and analyzer/test failures are not auto-edited.",
            "Safe recovery may run dart format . and therefore modify Dart files; inspect git_before and the final diff.",
            "No signing configuration is created, no credentials are invented, and nothing is published.",
            "A successful local build does not prove device quality, store compliance, or release signing."
        ]
    }

    if not project.is_dir():
        report["overall_status"] = "BLOCKED"
        report["error"] = "Project directory does not exist"
    elif not (project / "pubspec.yaml").is_file():
        report["overall_status"] = "BLOCKED"
        report["error"] = "pubspec.yaml not found; choose a Flutter project root"
    else:
        report["environment"] = {
            "flutter": command_version(["flutter", "--version"]),
            "dart": command_version(["dart", "--version"]),
            "java": command_version(["java", "-version"]),
            "git": command_version(["git", "--version"]),
        }
        if not report["environment"]["flutter"]["available"] and not args.dry_run:
            report["overall_status"] = "BLOCKED"
            report["error"] = "Flutter executable not found on PATH. Install Flutter and configure Android SDK before running."
        else:
            planned = [
                ("dependency_resolution", ["flutter", "pub", "get"]),
                ("format_check", ["dart", "format", "--output=none", "--set-exit-if-changed", "."]),
                ("static_analysis", ["flutter", "analyze"]),
            ]
            if not args.skip_tests:
                planned.append(("tests", ["flutter", "test"]))
            if args.build != "none":
                target = "apk" if args.build == "apk" else "appbundle"
                build_command = ["flutter", "build", target, "--release"]
                if args.flavor:
                    build_command.extend(["--flavor", args.flavor])
                build_command.extend(f"--dart-define={define}" for define in args.dart_define)
                planned.append(("release_build", build_command))

            if args.dry_run:
                report["overall_status"] = "DRY RUN"
                report["planned_commands"] = [{"step": n, "command": c} for n, c in planned]
            else:
                run_dir.mkdir(parents=True, exist_ok=True)
                failed = False
                format_repaired = False
                for step_name, cmd in planned:
                    attempts = 0
                    step = {"name": step_name, "command": cmd, "attempts": [], "status": "NOT RUN"}
                    while True:
                        attempts += 1
                        started = time.time()
                        try:
                            proc = subprocess.run(cmd, cwd=project, capture_output=True, text=True)
                            out = proc.stdout or ""
                            err = proc.stderr or ""
                            combined = out + ("\n" if out and err else "") + err
                            log_path = run_dir / f"{len(report['steps'])+1:02d}_{step_name}_attempt{attempts}.log"
                            log_path.write_text(
                                f"$ {' '.join(cmd)}\nexit_code={proc.returncode}\n\nSTDOUT:\n{out}\nSTDERR:\n{err}",
                                encoding="utf-8", errors="replace")
                            attempt_result = {
                                "attempt": attempts, "exit_code": proc.returncode,
                                "duration_seconds": round(time.time()-started, 2),
                                "failure_category": None if proc.returncode == 0 else classify_failure(combined),
                                "log": str(log_path), "stdout_tail": out.splitlines()[-12:],
                                "stderr_tail": err.splitlines()[-12:]
                            }
                        except OSError as exc:
                            attempt_result = {"attempt": attempts, "exit_code": 127,
                                              "duration_seconds": round(time.time()-started, 2),
                                              "failure_category": "TOOL_EXECUTION",
                                              "error": str(exc), "log": None}
                        step["attempts"].append(attempt_result)
                        if attempt_result["exit_code"] == 0:
                            step["status"] = "PASS"
                            break

                        can_retry = attempts <= args.max_retries
                        if step_name == "format_check" and args.fix_mode == "safe" and not format_repaired:
                            # One explicit, logged formatter invocation; source changes are visible in Git status/diff.
                            format_repaired = True
                            fix_cmd = ["dart", "format", "."]
                            report["recovery_actions"].append({"action": "format_dart_sources",
                                "reason": "Format check failed", "command": fix_cmd,
                                "warning": "This modifies Dart source formatting. Review the Git diff before accepting changes."})
                            if not shutil.which("dart"):
                                break
                            fix = subprocess.run(fix_cmd, cwd=project, capture_output=True, text=True)
                            fix_log = run_dir / "recovery_format_dart.log"
                            fix_log.write_text(f"$ {' '.join(fix_cmd)}\nexit_code={fix.returncode}\n\nSTDOUT:\n{fix.stdout}\nSTDERR:\n{fix.stderr}",
                                               encoding="utf-8", errors="replace")
                            report["recovery_actions"][-1].update({"exit_code": fix.returncode, "log": str(fix_log)})
                            if fix.returncode == 0:
                                continue
                            break
                        if step_name == "dependency_resolution" and can_retry:
                            report["recovery_actions"].append({"action": "retry_dependency_resolution",
                                "reason": "Initial flutter pub get failed", "attempt": attempts + 1})
                            continue
                        if step_name == "release_build" and can_retry:
                            # Safe retry after dependency resolution only; no clean/delete operation.
                            report["recovery_actions"].append({"action": "retry_build_after_pub_get",
                                "reason": "Initial release build failed", "attempt": attempts + 1})
                            dep = subprocess.run(["flutter", "pub", "get"], cwd=project,
                                                 capture_output=True, text=True)
                            dep_log = run_dir / "recovery_pub_get.log"
                            dep_log.write_text(f"$ flutter pub get\nexit_code={dep.returncode}\n\nSTDOUT:\n{dep.stdout}\nSTDERR:\n{dep.stderr}",
                                               encoding="utf-8", errors="replace")
                            report["recovery_actions"][-1].update({"pub_get_exit_code": dep.returncode,
                                                                   "log": str(dep_log)})
                            if dep.returncode == 0:
                                continue
                            break
                        break
                    report["steps"].append(step)
                    if step["status"] != "PASS":
                        failed = True
                        # Fail fast: downstream checks would be misleading if dependencies/analysis failed.
                        break
                if not failed and args.build != "none":
                    ext = ".apk" if args.build == "apk" else ".aab"
                    artifact_path = project / "build" / "app" / "outputs" / "flutter-apk"
                    # Correct bundle path is build/app/outputs/bundle/release/app-release.aab.
                    if ext == ".aab":
                        artifact_path = project / "build" / "app" / "outputs" / "bundle" / "release"
                    candidate = artifact_path / ("app-release" + ext)
                    report["artifact"] = {"expected_path": str(candidate),
                                          "exists": candidate.is_file(),
                                          "size_bytes": candidate.stat().st_size if candidate.is_file() else None}
                    if not candidate.is_file():
                        failed = True
                        report["recovery_actions"].append({"action": "artifact_verification",
                            "status": "FAIL", "reason": "Build command succeeded but expected release artifact was not found"})
                report["git_after"] = git_snapshot(project)
                report["overall_status"] = "FAIL" if failed else "PASS"
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    if not args.dry_run:
        try:
            run_dir.mkdir(parents=True, exist_ok=True)
            report_path = run_dir / "report.json"
            report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            report["report_path"] = str(report_path)
            report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        except OSError as exc:
            report["report_write_error"] = str(exc)
    print(json.dumps(report, indent=2))
    return 0 if report["overall_status"] in ("PASS", "DRY RUN") else 1

if __name__ == "__main__":
    sys.exit(main())
