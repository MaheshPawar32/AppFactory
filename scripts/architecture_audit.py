#!/usr/bin/env python3
"""Statically check Dart imports against conventional feature-layer boundaries."""
from pathlib import Path
import argparse
import json
import re
import sys

LAYERS = {"presentation", "application", "domain", "data"}
IMPORT_RE = re.compile(r"""(?m)^\s*(?:import|export|part)\s+['"]([^'"]+)['"]""")
PACKAGE_RE = re.compile(r"(?m)^name:\s*([A-Za-z0-9_]+)\s*$")


def _import_path(uri, source, lib, package_name):
    if uri.startswith("package:"):
        package_uri = uri[len("package:"):]
        prefix = f"{package_name}/"
        if not package_uri.startswith(prefix):
            return None
        candidate = (lib / package_uri[len(prefix):]).resolve()
        try:
            candidate.relative_to(lib.resolve())
        except ValueError:
            return None
        return candidate
    if uri.startswith("."):
        candidate = (source.parent / uri).resolve()
        try:
            candidate.relative_to(lib.resolve())
        except ValueError:
            return None
        return candidate
    return None


def audit(project: Path):
    project = project.expanduser().resolve()
    errors, warnings, checked = [], [], 0
    pubspec = project / "pubspec.yaml"
    lib = project / "lib"
    if not pubspec.is_file():
        return {
            "project": str(project),
            "status": "FAIL",
            "checked_files": 0,
            "errors": ["Missing pubspec.yaml"],
            "warnings": [],
            "note": "Static import-boundary audit only; it is not a full architecture review.",
        }
    if not lib.is_dir():
        return {
            "project": str(project),
            "status": "FAIL",
            "checked_files": 0,
            "errors": ["Missing lib/ directory"],
            "warnings": [],
            "note": "Static import-boundary audit only; it is not a full architecture review.",
        }
    match = PACKAGE_RE.search(pubspec.read_text(encoding="utf-8"))
    package_name = match.group(1) if match else ""
    for source in lib.rglob("*.dart"):
        try:
            relative = source.relative_to(lib)
        except ValueError:
            continue
        if "features" not in relative.parts:
            continue
        layer_positions = [
            index for index, part in enumerate(relative.parts) if part in LAYERS
        ]
        if not layer_positions:
            continue
        source_layer = relative.parts[layer_positions[0]]
        for uri in IMPORT_RE.findall(source.read_text(encoding="utf-8")):
            destination = _import_path(uri, source, lib, package_name)
            destination_parts = destination.relative_to(lib).parts if destination else ()
            destination_layer = next(
                (part for part in destination_parts if part in LAYERS), None
            )
            reason = None
            if source_layer == "domain":
                if uri.startswith("package:flutter/"):
                    reason = "domain must not depend on Flutter"
                elif destination_layer in {"presentation", "application", "data"}:
                    reason = f"domain must not depend on {destination_layer}"
            elif source_layer == "data" and destination_layer in {
                "presentation", "application",
            }:
                reason = f"data must not depend on {destination_layer}"
            elif source_layer == "application" and destination_layer == "presentation":
                reason = "application must not depend on presentation"
            elif source_layer == "presentation" and destination_layer == "data":
                reason = "presentation must not depend directly on data"
            if reason:
                errors.append({
                    "file": relative.as_posix(),
                    "import": uri,
                    "reason": reason,
                })
        checked += 1

    layer_files = [
        path for path in lib.rglob("*.dart")
        if any(part in LAYERS for part in path.relative_to(lib).parts)
    ]
    if not layer_files:
        warnings.append(
            "No recognized feature-layer Dart files found; architecture boundaries were not exercised"
        )
    return {
        "project": str(project),
        "status": "FAIL" if errors else ("PARTIAL" if warnings else "PASS"),
        "checked_files": checked,
        "errors": errors,
        "warnings": warnings,
        "note": "Static import-boundary audit only; it is not a full architecture review.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Flutter project directory")
    parser.add_argument("--json", action="store_true", help="Print JSON result")
    args = parser.parse_args(argv)
    result = audit(args.project)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Architecture audit: {result['status']} ({result['project']})")
        print(f"Layer files checked: {result['checked_files']}")
        for error in result["errors"]:
            print(f"ERROR: {error['file']}: {error['reason']} ({error['import']})")
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
        print(result["note"])
    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
