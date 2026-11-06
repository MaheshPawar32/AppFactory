#!/usr/bin/env python3
"""Validate or safely migrate MyAppFactory APP_CONFIG.json files."""
from copy import deepcopy
from pathlib import Path
import argparse
import json
import re
import sys

PACKAGE_RE = re.compile(r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*)+$")
REQUIRED_PATHS = (
    ("app", "name"), ("app", "package_name"), ("app", "version"),
    ("architecture", "state_management"), ("architecture", "storage"),
    ("integrations", "backend"), ("design", "locales"),
)
ENVIRONMENTS = ("development", "staging", "production")
PLACEHOLDERS = ("REPLACE_", "RECORD_ACTUAL_", "TODO", "CHANGEME")


def _read_config(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, ["File not found"]
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"Cannot read valid JSON: {exc}"]
    if not isinstance(data, dict):
        return None, ["Root must be a JSON object"]
    return data, []


def validate(path: Path):
    data, read_errors = _read_config(path)
    if read_errors:
        return {"file": str(path), "valid": False, "errors": read_errors, "warnings": []}

    errors, warnings = [], []
    version = data.get("schema_version", 1)
    if type(version) is not int or version not in (1, 2):
        errors.append("schema_version must be 1 or 2")
    for group, key in REQUIRED_PATHS:
        section = data.get(group)
        value = section.get(key) if isinstance(section, dict) else None
        if value is None or value == "" or value == []:
            errors.append(f"Missing required value: {group}.{key}")
        elif (group, key) == ("design", "locales"):
            if not isinstance(value, list) or not all(
                isinstance(locale, str) and locale for locale in value
            ):
                errors.append("design.locales must be a non-empty list of locale strings")
        elif not isinstance(value, str):
            errors.append(f"{group}.{key} must be a string")
        elif isinstance(value, str) and any(
            token.lower() in value.lower() for token in PLACEHOLDERS
        ):
            warnings.append(f"Placeholder remains: {group}.{key}")

    app = data.get("app", {})
    package = app.get("package_name", "") if isinstance(app, dict) else ""
    if package and not PACKAGE_RE.fullmatch(str(package)):
        errors.append("app.package_name is not reverse-domain style")

    if version == 2:
        for key in ("branding", "environments", "build", "store", "release"):
            if not isinstance(data.get(key), dict):
                errors.append(f"schema_version 2 requires object: {key}")
        environments = data.get("environments")
        if isinstance(environments, dict):
            unknown = sorted(set(environments) - set(ENVIRONMENTS))
            if unknown:
                errors.append(f"Unknown environment(s): {', '.join(unknown)}")
            for environment in ENVIRONMENTS:
                if environment not in environments:
                    errors.append(f"Missing environment configuration: {environment}")
                elif not isinstance(environments[environment], dict):
                    errors.append(f"Environment configuration must be an object: {environment}")
                else:
                    environment_config = environments[environment]
                    if not isinstance(environment_config.get("api_base_url", ""), str):
                        errors.append(f"{environment}.api_base_url must be a string")
                    required = environment_config.get("required_variables", [])
                    if not isinstance(required, list) or not all(
                        isinstance(item, str) and item for item in required
                    ):
                        errors.append(f"{environment}.required_variables must be a list of strings")
        build = data.get("build")
        if isinstance(build, dict):
            android = build.get("android")
            if not isinstance(android, dict):
                errors.append("schema_version 2 requires object: build.android")
            else:
                application_id = android.get("application_id")
                if application_id and not PACKAGE_RE.fullmatch(str(application_id)):
                    errors.append("build.android.application_id is not reverse-domain style")
                elif application_id and application_id != package:
                    errors.append("build.android.application_id contradicts app.package_name")
                minimum = android.get("min_sdk")
                target = android.get("target_sdk")
                if isinstance(minimum, int) and minimum < 21:
                    errors.append("build.android.min_sdk must be at least 21")
                if isinstance(target, int) and isinstance(minimum, int) and target < minimum:
                    errors.append("build.android.target_sdk must be >= min_sdk")

    integrations = data.get("integrations", {})
    if isinstance(integrations, dict):
        backend = integrations.get("backend")
        if integrations.get("firebase_enabled") is True and not integrations.get("firebase_services"):
            warnings.append("Firebase enabled but firebase_services is empty; confirm this is intentional")
        if integrations.get("admob_enabled") is True and not integrations.get("admob_formats"):
            warnings.append("AdMob enabled but admob_formats is empty; confirm this is intentional")
        if integrations.get("firebase_enabled") is True and backend not in ("firebase", None):
            errors.append("integrations.firebase_enabled contradicts integrations.backend")
        if integrations.get("firebase_enabled") is False and backend == "firebase":
            errors.append("integrations.backend is firebase but firebase_enabled is false")

    constraints = data.get("constraints", {})
    if (
        isinstance(app, dict)
        and app.get("project_type") == "existing"
        and isinstance(constraints, dict)
        and constraints.get("preserve_existing_features") is not True
    ):
        warnings.append("Existing project should normally preserve existing features")
    return {
        "file": str(path),
        "valid": not errors,
        "schema_version": version,
        "errors": errors,
        "warnings": warnings,
        "note": "Schema sanity check only; it does not verify app code, credentials or integrations.",
    }


def migrate_to_v2(data):
    """Return a non-destructive additive migration; existing values always win."""
    if not isinstance(data, dict):
        raise ValueError("Config root must be an object")
    old_version = data.get("schema_version", 1)
    if type(old_version) is not int or old_version not in (1, 2):
        raise ValueError(f"Cannot migrate unsupported schema_version: {old_version}")
    migrated = deepcopy(data)
    if old_version == 2:
        return migrated
    app = migrated.get("app")
    if not isinstance(app, dict):
        raise ValueError("Cannot migrate config without an app object")
    name = str(app.get("name", ""))
    defaults = {
        "branding": {
            "primary_color": "#6366F1",
            "launcher_icon": {"status": "NOT PROVIDED", "source": ""},
            "splash_screen": {"status": "NOT PROVIDED", "source": ""},
            "store_icon": {"status": "NOT PROVIDED", "source": ""},
        },
        "environments": {
            environment: {"api_base_url": "", "required_variables": []}
            for environment in ENVIRONMENTS
        },
        "build": {
            "android": {
                "application_id": app.get("package_name", ""),
                "min_sdk": "flutter.minSdkVersion",
                "target_sdk": "flutter.targetSdkVersion",
                "gradle_flavors": list(ENVIRONMENTS),
            }
        },
        "store": {
            "title": name,
            "short_description": "",
            "full_description": "",
            "assets": {
                "icon": "NOT PROVIDED",
                "feature_graphic": "NOT PROVIDED",
                "phone_screenshots": "NOT CAPTURED",
            },
        },
        "release": {
            "signing": "NOT CONFIGURED",
            "upload": "NOT AUTHORIZED",
            "publish": "NOT AUTHORIZED",
        },
    }
    for section, values in defaults.items():
        existing = migrated.get(section)
        if not isinstance(existing, dict):
            migrated[section] = values
            continue
        for key, value in values.items():
            if key not in existing:
                existing[key] = value
            elif isinstance(value, dict) and isinstance(existing[key], dict):
                for nested_key, nested_value in value.items():
                    existing[key].setdefault(nested_key, nested_value)
    migrated.setdefault("schema_version", 2)
    migrated["schema_version"] = 2
    return migrated


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="Path to APP_CONFIG.json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--migrate-to-v2", action="store_true")
    parser.add_argument("--output", type=Path, help="New migration output; never overwrites")
    args = parser.parse_args(argv)
    if args.migrate_to_v2:
        if args.output is None:
            parser.error("--migrate-to-v2 requires --output")
        data, errors = _read_config(args.config)
        if errors:
            result = {"file": str(args.config), "valid": False, "errors": errors}
            print(json.dumps(result, indent=2))
            return 1
        output = args.output
        try:
            migrated = migrate_to_v2(data)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf-8") as file:
                file.write(json.dumps(migrated, indent=2) + "\n")
        except (OSError, ValueError) as exc:
            print(json.dumps({"status": "BLOCKED", "error": str(exc)}, indent=2), file=sys.stderr)
            return 2
        result = validate(output)
        result["migration"] = "v1-to-v2 additive copy; source preserved"
        print(json.dumps(result, indent=2) if args.json else
              f"Migration output: {output}\nSchema status: {'VALID' if result['valid'] else 'INVALID'}")
        return 0 if result["valid"] else 1

    result = validate(args.config)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"App config: {result['file']}")
        print("Schema status:", "VALID" if result["valid"] else "INVALID")
        for issue in result["errors"]:
            print("ERROR:", issue)
        for issue in result["warnings"]:
            print("WARNING:", issue)
        print(result["note"])
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
