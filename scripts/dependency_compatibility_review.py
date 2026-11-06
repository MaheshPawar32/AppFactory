#!/usr/bin/env python3
"""Review pubspec dependency constraints without installing packages or changing files."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

try:
    import yaml  # optional PyYAML
except ImportError:
    yaml = None

def parse_pubspec(path: Path):
    raw = path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(raw) or {}
        if not isinstance(data, dict):
            raise ValueError("pubspec.yaml root must be a mapping")
        return data, raw
    # Conservative fallback: top-level package sections and scalar constraints only.
    section = None
    data = {"dependencies": {}, "dev_dependencies": {}, "dependency_overrides": {}}
    for lineno, line in enumerate(raw.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" ") and re.match(r"^[A-Za-z_][\w-]*\s*:", line):
            section = line.split(":", 1)[0].strip()
            continue
        if section in data and line.startswith("  ") and not line.startswith("    "):
            match = re.match(r"^\s{2}([A-Za-z0-9_]+)\s*:\s*(.*?)\s*$", line)
            if match:
                value = match.group(2).split("#", 1)[0].strip().strip('"\'')
                data[section][match.group(1)] = value
    return data, raw

def audit_pubspec(path):
    path = Path(path)
    errors, warnings, dependencies = [], [], []
    if not path.is_file():
        return {"valid": False, "errors": [f"pubspec.yaml not found: {path}"], "warnings": [], "dependencies": []}
    try:
        data, raw = parse_pubspec(path)
    except Exception as exc:
        return {"valid": False, "errors": [f"Unable to parse pubspec.yaml: {exc}"], "warnings": [], "dependencies": []}
    for section in ("dependencies", "dev_dependencies", "dependency_overrides"):
        values = data.get(section, {}) or {}
        if not isinstance(values, dict):
            errors.append(f"{section} must be a mapping")
            continue
        for name, value in values.items():
            if isinstance(value, dict):
                source = "git/path/sdk or structured source"
                constraint = None
            else:
                source = "hosted/scalar"
                constraint = str(value).strip()
            if name == "flutter":
                continue
            item = {"name": str(name), "section": section, "source": source, "constraint": constraint}
            dependencies.append(item)
            if section == "dependency_overrides":
                warnings.append(f"{name}: dependency override present; verify necessity and transitive impact")
            if constraint is not None and (constraint in ("any", "") or constraint.startswith("any ")):
                warnings.append(f"{name}: unconstrained dependency (`{constraint}`); inspect lockfile and upgrade policy")
            if constraint and re.match(r"^[0-9]+\.[0-9]+\.[0-9]+$", constraint):
                warnings.append(f"{name}: exact version pin `{constraint}` may constrain compatible updates")
    sdk = ((data.get("environment") or {}).get("sdk") if isinstance(data.get("environment") or {}, dict) else None)
    if not sdk:
        warnings.append("Dart SDK constraint is missing; verify supported SDK range")
    if "dependency_overrides:" in raw and not data.get("dependency_overrides"):
        warnings.append("dependency_overrides section detected but parsed entries were empty; inspect YAML manually")
    return {"valid": not errors, "errors": errors, "warnings": warnings, "sdk_constraint": sdk, "dependencies": dependencies}

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("flutter_project", type=Path)
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    result = audit_pubspec(a.flutter_project / "pubspec.yaml" if a.flutter_project.is_dir() else a.flutter_project)
    print(json.dumps(result, indent=2) if a.json else
          ("Dependency review: " + ("PASS" if result["valid"] else "FAIL") + "\n" +
           "\n".join("ERROR: " + x for x in result["errors"]) + "\n" +
           "\n".join("WARN: " + x for x in result["warnings"]) + "\n" +
           f"Dependencies inspected: {len(result['dependencies'])}"))
    return 0 if result["valid"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
