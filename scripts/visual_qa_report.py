#!/usr/bin/env python3
"""Report visual/device QA tracker completeness; never claims screenshots are visually correct."""
from pathlib import Path
import argparse, csv, json, sys

ROOT = Path(__file__).resolve().parents[1]
def load_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=ROOT, help="Project root containing templates/project_docs or project docs.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    base = args.project.resolve()
    candidates = [
        base / "VISUAL_QA_LOG.md",
        base / "docs" / "VISUAL_QA_LOG.md",
        base / "templates" / "project_docs" / "VISUAL_QA_LOG.md",
    ]
    log_path = next((p for p in candidates if p.is_file()), None)
    matrix_candidates = [
        base / "DEVICE_TEST_MATRIX.csv",
        base / "docs" / "DEVICE_TEST_MATRIX.csv",
        base / "templates" / "project_docs" / "DEVICE_TEST_MATRIX.csv",
    ]
    matrix_path = next((p for p in matrix_candidates if p.is_file()), None)
    result = {
        "project": str(base),
        "visual_qa_log_found": bool(log_path),
        "visual_qa_log_path": str(log_path) if log_path else None,
        "device_matrix_found": bool(matrix_path),
        "device_matrix_path": str(matrix_path) if matrix_path else None,
        "device_tests": {"total": 0, "pass": 0, "fail": 0, "blocked": 0, "not_run": 0, "other": 0},
        "note": "Tracker completeness only. No screenshot pixels or runtime UI were inspected."
    }
    if matrix_path:
        try:
            rows = load_csv(matrix_path)
            result["device_tests"]["total"] = len(rows)
            for row in rows:
                status = (row.get("status") or "NOT RUN").strip().lower().replace(" ", "_")
                if status in ("pass", "fail", "blocked", "not_run"):
                    result["device_tests"][status] += 1
                else:
                    result["device_tests"]["other"] += 1
        except (OSError, csv.Error) as exc:
            result["device_matrix_error"] = str(exc)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Visual QA evidence report (read-only)")
        for key, value in result.items():
            print(f"{key}: {value}")
        print("This is not a visual regression pass/fail assessment.")
    return 0 if log_path and matrix_path else 1

if __name__ == "__main__":
    sys.exit(main())
