#!/usr/bin/env python3
"""Summarize an asset/license inventory CSV and flag incomplete records."""
from pathlib import Path
import argparse, csv, json, sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "templates" / "project_docs" / "ASSET_LICENSE_INVENTORY.csv"
REQUIRED = ("Asset ID", "Asset / package", "Source URL or package", "License", "File path / version", "Review status")

def inspect(path: Path):
    errors, warnings = [], []
    rows = []
    try:
        with path.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            missing = [h for h in REQUIRED if h not in (reader.fieldnames or [])]
            if missing:
                errors.append("Missing columns: " + ", ".join(missing))
            rows = list(reader)
    except FileNotFoundError:
        errors.append("Inventory CSV not found")
    except (OSError, csv.Error) as exc:
        errors.append(f"Cannot read inventory: {exc}")
    incomplete = []
    for index, row in enumerate(rows, start=2):
        if not any((v or "").strip() for v in row.values()):
            continue
        missing_fields = [h for h in REQUIRED[:-1] if not (row.get(h) or "").strip()]
        status = (row.get("Review status") or "").strip().upper()
        if missing_fields or status not in {"PASS", "REVIEWED", "NOT REVIEWED", "BLOCKED"}:
            incomplete.append({"row": index, "missing_fields": missing_fields, "review_status": status or "NOT RECORDED"})
        elif status in {"NOT REVIEWED", "BLOCKED"}:
            incomplete.append({"row": index, "missing_fields": [], "review_status": status})
    if incomplete:
        warnings.append(f"{len(incomplete)} inventory row(s) need completion or human review")
    return {"file": str(path), "valid": not errors, "assets": len(rows), "needs_review": incomplete,
            "errors": errors, "warnings": warnings,
            "note": "This checks inventory completeness only; it does not determine whether a license is legally sufficient."}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=DEFAULT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = inspect(args.file)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Asset license inventory: {result['file']}\nRows: {result['assets']}\nNeeds review: {len(result['needs_review'])}")
        for x in result["errors"]: print("ERROR:", x)
        for x in result["warnings"]: print("WARNING:", x)
        print(result["note"])
    return 0 if result["valid"] else 1

if __name__ == "__main__":
    sys.exit(main())
