#!/usr/bin/env python3
"""Read-only MyAppFactory status dashboard. Uses only Python's standard library."""
from pathlib import Path
import argparse, csv, json, sys

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "apps" / "PROJECT_REGISTRY.csv"
STATUS_FIELDS = ("last_analyzer_status", "last_test_status", "last_build_status")

def read_registry():
    if not REGISTRY.exists():
        return [], ["Project registry is missing."]
    with REGISTRY.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return [], ["Project registry has no header."]
        return list(reader), []

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()
    rows, warnings = read_registry()
    output = []
    for row in rows:
        name = (row.get("app_name") or "").strip()
        if not name:
            continue
        # The registry does not currently mandate a path; do not guess one.
        path = (row.get("project_path") or "").strip()
        statuses = {field: (row.get(field) or "NOT RECORDED").strip() for field in STATUS_FIELDS}
        output.append({
            "app_name": name,
            "package_name": (row.get("package_name") or "").strip() or "NOT RECORDED",
            "current_stage": (row.get("current_stage") or "").strip() or "NOT RECORDED",
            "project_path": path or "NOT RECORDED",
            "project_path_exists": (ROOT / path).is_dir() if path and not Path(path).is_absolute() else (Path(path).is_dir() if path else None),
            "verification": statuses,
            "known_issues": (row.get("known_issues") or "").strip(),
            "next_action": (row.get("next_action") or "").strip() or "Record the next concrete action.",
        })
    if args.json:
        print(json.dumps({"registry": str(REGISTRY.relative_to(ROOT)), "projects": output, "warnings": warnings}, indent=2))
        return 0
    print("MyAppFactory Developer Dashboard (read-only)")
    print("Registry:", REGISTRY.relative_to(ROOT))
    if not output:
        print("No app entries recorded. This is not a failure; add projects to the registry.")
    for item in output:
        print(f"\n{item['app_name']} [{item['package_name']}]")
        print(f"  Stage: {item['current_stage']}")
        print(f"  Path: {item['project_path']} (exists: {item['project_path_exists']})")
        for key, value in item["verification"].items():
            print(f"  {key}: {value}")
        print(f"  Known issues: {item['known_issues'] or 'None recorded'}")
        print(f"  Next action: {item['next_action']}")
    for warning in warnings:
        print("WARNING:", warning)
    print("\nStatuses are registry records only; this script does not run Flutter tests or builds.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
