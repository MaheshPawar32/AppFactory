#!/usr/bin/env python3
"""Validate feature-module selections and generate a safe implementation brief."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "templates" / "feature_modules" / "catalog.json"
VALID_STATUSES = {"not configured", "configured", "tested", "not applicable"}

def load_catalog(path=CATALOG):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("modules"), dict):
        raise ValueError("Unsupported or malformed feature-module catalog")
    return data["modules"]

def validate_manifest(path, catalog=None):
    catalog = catalog or load_catalog()
    errors, warnings = [], []
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"valid": False, "errors": [str(exc)], "warnings": [], "selected": []}
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    selected = data.get("selected_modules", [])
    if not isinstance(selected, list):
        errors.append("selected_modules must be a list")
        selected = []
    seen = set()
    for entry in selected:
        if not isinstance(entry, dict):
            errors.append("each selected_modules entry must be an object")
            continue
        module_id = entry.get("id")
        if module_id not in catalog:
            errors.append(f"unknown module id: {module_id}")
            continue
        if module_id in seen:
            errors.append(f"duplicate module id: {module_id}")
        seen.add(module_id)
        choice = entry.get("choice")
        if choice not in catalog[module_id].get("choices", []):
            errors.append(f"{module_id}: choice must be one of {catalog[module_id].get('choices', [])}")
        status = entry.get("status", "not configured")
        if status not in VALID_STATUSES:
            errors.append(f"{module_id}: invalid status '{status}'")
        if status == "tested" and not entry.get("evidence"):
            errors.append(f"{module_id}: tested status requires evidence")
        if module_id.endswith("_optional") and status == "configured" and not entry.get("approved", False):
            warnings.append(f"{module_id}: optional integration is configured without explicit approved=true")
    return {"valid": not errors, "errors": errors, "warnings": warnings,
            "selected": [e.get("id") for e in selected if isinstance(e, dict)]}

def generate_prompt(path, catalog=None):
    catalog = catalog or load_catalog()
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    result = validate_manifest(path, catalog)
    if not result["valid"]:
        raise ValueError("; ".join(result["errors"]))
    lines = [
        "# MyAppFactory Feature Module Implementation Brief", "",
        "Implement only the selected feature modules in the existing Flutter app.",
        "Preserve existing screens, navigation, state management, design system, user data, and behavior.",
        "Do not rewrite the project or copy the starter over it. Inspect files and Git status first.",
        "Do not add packages until compatibility and necessity are reviewed. Never invent credentials.",
        "Run format, analyze, tests, and relevant device checks; report each as PASS/FAIL/BLOCKED/NOT RUN with evidence.", ""
    ]
    app = data.get("app", {})
    lines += [f"App: {app.get('name', 'Not specified')}", f"Flutter project path: {app.get('path', 'Not specified')}", ""]
    for entry in data.get("selected_modules", []):
        m = catalog[entry["id"]]
        lines += [f"## {m['title']} (`{entry['id']}`)", m["purpose"],
                  f"Selected choice: `{entry['choice']}`",
                  f"Current status: `{entry.get('status', 'not configured')}`",
                  "Dependencies to review (not automatically approved): " + ", ".join(m["dependencies"]["optional"]), "",
                  "Acceptance criteria:"]
        lines += [f"- [ ] {x}" for x in m["acceptance"]]
        lines.append("")
    lines += ["## Required deliverables", "- Updated implementation and focused tests.",
              "- Dependency review with reasons and versions actually resolved.",
              "- Update app architecture and module status/evidence documents.",
              "- Summarize changed files, commands actually run, results, known risks and manual steps.",
              "- Do not mark a module tested without runtime/test evidence."]
    return "\n".join(lines) + "\n"

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    ls = sub.add_parser("list", help="List available modules")
    val = sub.add_parser("validate", help="Validate a module selection manifest")
    val.add_argument("manifest", type=Path)
    prompt = sub.add_parser("prompt", help="Generate a Claude Code implementation prompt")
    prompt.add_argument("manifest", type=Path)
    prompt.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    catalog = load_catalog()
    if args.command == "list":
        for key, value in catalog.items():
            print(f"{key}: {value['title']}")
        return 0
    if args.command == "validate":
        result = validate_manifest(args.manifest, catalog)
        print(json.dumps(result, indent=2))
        return 0 if result["valid"] else 1
    try:
        result = generate_prompt(args.manifest, catalog)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(result, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
