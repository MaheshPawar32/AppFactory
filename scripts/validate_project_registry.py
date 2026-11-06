#!/usr/bin/env python3
"""Check project registry rows and status vocabulary; read-only, standard library only."""
from pathlib import Path
import argparse, csv, json, sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "apps" / "PROJECT_REGISTRY.csv"
ALLOWED = {"PASS", "FAIL", "BLOCKED", "NOT RUN", "NOT RECORDED", "REVIEW", "INFO", "NOT VERIFIED"}

def validate(path: Path):
    errors, warnings, entries = [], [], 0
    required = {"app_name", "package_name", "current_stage", "last_analyzer_status",
                "last_test_status", "last_build_status", "next_action"}
    try:
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = set(reader.fieldnames or [])
            missing = sorted(required - headers)
            if missing:
                errors.append("Missing required columns: " + ", ".join(missing))
            seen = set()
            for line, row in enumerate(reader, start=2):
                if not any((v or "").strip() for v in row.values()):
                    continue
                entries += 1
                name = (row.get("app_name") or "").strip()
                package = (row.get("package_name") or "").strip()
                if not name:
                    errors.append(f"Row {line}: app_name is required")
                elif name.casefold() in seen:
                    errors.append(f"Row {line}: duplicate app_name {name!r}")
                else:
                    seen.add(name.casefold())
                if not package:
                    warnings.append(f"Row {line}: package_name not recorded")
                for key in ("last_analyzer_status", "last_test_status", "last_build_status"):
                    value = (row.get(key) or "").strip().upper()
                    if value and value not in ALLOWED:
                        warnings.append(f"Row {line}: unfamiliar status {key}={value!r}; prefer explicit status vocabulary")
                if not (row.get("next_action") or "").strip():
                    warnings.append(f"Row {line}: next_action is empty")
    except FileNotFoundError:
        errors.append("Registry file not found")
    except (OSError, csv.Error) as exc:
        errors.append(f"Could not read registry: {exc}")
    return {"file": str(path), "valid": not errors, "entries": entries, "errors": errors, "warnings": warnings,
            "note": "This validates registry consistency only; it does not run or verify project builds/tests."}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=DEFAULT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate(args.file)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Registry: {result['file']}\nEntries: {result['entries']}\nStatus: {'VALID' if result['valid'] else 'INVALID'}")
        for x in result["errors"]: print("ERROR:", x)
        for x in result["warnings"]: print("WARNING:", x)
        print(result["note"])
    return 0 if result["valid"] else 1

if __name__ == "__main__":
    sys.exit(main())
