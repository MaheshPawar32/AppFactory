#!/usr/bin/env python3
"""Run a safe, consolidated set of MyAppFactory checks and write a JSON report."""
from pathlib import Path
import argparse, json, subprocess, sys, time

ROOT = Path(__file__).resolve().parents[1]
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=Path("docs/last_factory_check_report.json"))
    parser.add_argument("--strict", action="store_true", help="Return non-zero if any selected check fails")
    args = parser.parse_args()
    checks = [
        ("Python unit tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]),
        ("App config validator", [sys.executable, "scripts/validate_app_config.py", "templates/project_docs/APP_CONFIG.json"]),
        ("Project registry validator", [sys.executable, "scripts/validate_project_registry.py"]),
        ("Asset license inventory report", [sys.executable, "scripts/asset_license_report.py"]),
        ("Template sync", [sys.executable, "scripts/check_template_sync.py"]),
        ("Template update preview", [sys.executable, "scripts/template_update_preview.py"]),
        ("Project dashboard", [sys.executable, "scripts/project_dashboard.py", "--json"]),
        ("Visual QA report", [sys.executable, "scripts/visual_qa_report.py"]),
        ("Project audit", [sys.executable, "scripts/project_audit.py"]),
        ("V4 quality QA dry run", [
            sys.executable, "scripts/quality_qa_engine.py",
            "design_system/nova_ui_flutter", "--check", "all",
        ]),
    ]
    results = []
    for name, cmd in checks:
        start = time.time()
        try:
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=45)
            status = "PASS" if proc.returncode == 0 else "FAIL"
            detail = (proc.stdout or "").strip().splitlines()[-1:] 
            stderr_lines = (proc.stderr or "").strip().splitlines()
            # Preserve only a short stderr tail; environment warm-up warnings may be unrelated.
            results.append({"name": name, "status": status, "exit_code": proc.returncode,
                            "duration_seconds": round(time.time()-start, 2),
                            "summary": detail[0] if detail else "",
                            "stderr_tail": stderr_lines[-2:]})
        except subprocess.TimeoutExpired:
            results.append({"name": name, "status": "TIMEOUT", "exit_code": None,
                            "duration_seconds": round(time.time()-start, 2),
                            "summary": "Timed out after 45 seconds", "stderr_tail": []})
    report = {"tool": "MyAppFactory consolidated checks", "read_only": True,
              "checks": results, "passed": all(x["status"] == "PASS" for x in results),
              "note": "These checks do not compile, analyze, test, or build any Flutter app. Run Flutter commands separately in each app."}
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 1 if args.strict and not report["passed"] else 0
if __name__ == "__main__":
    sys.exit(main())
