#!/usr/bin/env python3
"""Read-only structural validation for a Flutter app workspace; no build is performed."""
from pathlib import Path
import argparse, json, re, sys

PACKAGE_RE = re.compile(r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*)+$")

def inspect(project: Path):
    findings = []
    def add(check, status, detail):
        findings.append({"check": check, "status": status, "detail": detail})
    pubspec = project / "pubspec.yaml"
    if not pubspec.is_file():
        add("pubspec.yaml", "FAIL", "Missing; choose a Flutter project root")
        return {"project": str(project), "findings": findings, "passed": False,
                "note": "Structural validation only; no Flutter build or analyzer was run."}
    text = pubspec.read_text(encoding="utf-8", errors="replace")
    name_m = re.search(r"(?m)^name:\s*([A-Za-z0-9_]+)\s*(?:#.*)?$", text)
    add("pubspec package name", "PASS" if name_m else "REVIEW",
        name_m.group(1) if name_m else "Could not parse a simple pubspec name")
    android = project / "android"
    add("Android scaffolding", "PASS" if android.is_dir() else "FAIL",
        "android/ exists" if android.is_dir() else "android/ missing; run flutter create . only after backing up and reviewing the project")
    gradle_files = [android / "app" / "build.gradle", android / "app" / "build.gradle.kts"]
    gradle = next((p for p in gradle_files if p.is_file()), None)
    add("Android app Gradle file", "PASS" if gradle else "FAIL",
        str(gradle.relative_to(project)) if gradle else "Expected android/app/build.gradle or build.gradle.kts")
    if gradle:
        gtext = gradle.read_text(encoding="utf-8", errors="replace")
        app_ids = re.findall(r"""(?m)^\s*applicationId\s*(?:=\s*)?["']([^"']+)["']""", gtext)
        namespaces = re.findall(r"""(?m)^\s*namespace\s*(?:=\s*)?["']([^"']+)["']""", gtext)
        for label, vals in (("applicationId", app_ids), ("namespace", namespaces)):
            if vals:
                valid = all(PACKAGE_RE.fullmatch(v) for v in vals)
                add(label, "PASS" if valid else "FAIL", ", ".join(vals))
            else:
                add(label, "REVIEW", "Not found with the conservative parser; inspect Gradle manually")
        if app_ids and namespaces and app_ids[0] != namespaces[0]:
            add("applicationId/namespace consistency", "REVIEW",
                "They differ; this can be intentional, verify before release")
    else:
        add("applicationId", "NOT RUN", "No Gradle file available")
    for rel, label in [
        ("lib", "Dart source directory"),
        ("test", "Test directory"),
        (".gitignore", "Git ignore"),
    ]:
        p = project / rel
        exists = p.is_dir() if rel in ("lib", "test") else p.is_file()
        add(label, "PASS" if exists else "REVIEW", "Present" if exists else "Missing")
    # Common Android safety configuration checks; findings are prompts for review, not proof.
    manifest = android / "app" / "src" / "main" / "AndroidManifest.xml"
    if manifest.is_file():
        mtext = manifest.read_text(encoding="utf-8", errors="replace")
        cleartext = bool(re.search(r'usesCleartextTraffic\s*=\s*["\']true["\']', mtext))
        add("Cleartext traffic flag", "REVIEW" if cleartext else "INFO",
            "usesCleartextTraffic=true found; confirm a documented need" if cleartext else "No explicit true flag found by simple scan")
        permissions = sorted(set(re.findall(r'<uses-permission\b[^>]*android:name\s*=\s*["\']([^"\']+)', mtext)))
        add("Declared permissions inventory", "INFO",
            ", ".join(permissions) if permissions else "No uses-permission entries detected; check merged manifests and plugins too")
    else:
        add("Android manifest", "REVIEW", "Main manifest missing or nonstandard path")
    passed = not any(f["status"] == "FAIL" for f in findings)
    return {"project": str(project), "findings": findings, "passed": passed,
            "note": "Structural checks only. This does not run Flutter, inspect merged manifests, prove package correctness, scan all secrets, or certify security/store compliance."}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = inspect(args.project.expanduser().resolve())
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Flutter project structural validation:", result["project"])
        for f in result["findings"]:
            print(f"[{f['status']}] {f['check']}: {f['detail']}")
        print(result["note"])
    return 0 if result["passed"] else 1

if __name__ == "__main__":
    sys.exit(main())
