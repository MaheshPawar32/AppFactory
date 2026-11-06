#!/usr/bin/env python3
"""Evidence-based release readiness preflight; reports checks without claiming to build."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

def run_check(name, cmd, cwd, required=True):
    try:
        p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=300)
        status = "PASS" if p.returncode == 0 else ("FAIL" if required else "WARN")
        return {"name": name, "status": status, "command": cmd, "exit_code": p.returncode,
                "stdout_tail": p.stdout[-1500:], "stderr_tail": p.stderr[-1500:]}
    except FileNotFoundError as exc:
        return {"name": name, "status": "BLOCKED" if required else "WARN", "command": cmd, "error": str(exc)}
    except subprocess.TimeoutExpired:
        return {"name": name, "status": "BLOCKED" if required else "WARN", "command": cmd, "error": "timed out after 300 seconds"}

def preflight(project: Path, run_flutter: bool = False):
    checks = []
    for rel, label in [("pubspec.yaml", "Flutter project manifest"), ("lib", "Dart source folder"), ("test", "Test folder")]:
        exists = (project / rel).exists()
        checks.append({"name": label, "status": "PASS" if exists else ("WARN" if rel == "test" else "FAIL"),
                       "path": rel, "exists": exists})
    if not (project / "pubspec.yaml").is_file():
        return {"project": str(project), "status": "BLOCKED", "checks": checks,
                "note": "Not a Flutter project. No Flutter commands were run."}
    if run_flutter:
        checks += [
            run_check("Dart format check", ["dart", "format", "--set-exit-if-changed", "lib", "test"], project),
            run_check("Flutter analyze", ["flutter", "analyze"], project),
            run_check("Flutter tests", ["flutter", "test"], project, required=False),
        ]
    statuses = [x["status"] for x in checks]
    status = "FAIL" if "FAIL" in statuses else ("BLOCKED" if "BLOCKED" in statuses else ("WARN" if "WARN" in statuses else "PASS"))
    return {"project": str(project), "status": status, "checks": checks,
            "note": "This preflight does not build, sign, upload, or publish an app. Review release configuration and run device tests before release."}

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("project", type=Path)
    p.add_argument("--run-flutter-checks", action="store_true", help="Run format, analyze and tests when Flutter is installed")
    p.add_argument("--output", type=Path)
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    report = preflight(a.project.resolve(), a.run_flutter_checks)
    rendered = json.dumps(report, indent=2)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered if a.json or not a.output else f"Release preflight written to {a.output}\nStatus: {report['status']}")
    return 0 if report["status"] in ("PASS", "WARN") else 1

if __name__ == "__main__":
    raise SystemExit(main())
