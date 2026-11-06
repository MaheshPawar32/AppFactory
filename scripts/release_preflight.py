#!/usr/bin/env python3
"""Read-only release preflight for a Flutter project; not a security scanner or store certification."""
from pathlib import Path
import argparse, json, re, sys

def inspect(project: Path):
    findings = []
    def add(name, status, detail):
        findings.append({"check": name, "status": status, "detail": detail})
    pubspec = project / "pubspec.yaml"
    if pubspec.is_file():
        text = pubspec.read_text(encoding="utf-8", errors="replace")
        name = re.search(r"(?m)^name:\s*([^\s#]+)", text)
        version = re.search(r"(?m)^version:\s*([^\s#]+)", text)
        add("pubspec.yaml", "PASS", "Found pubspec.yaml")
        add("Package name", "REVIEW" if not name else "INFO", name.group(1) if name else "Could not parse name")
        add("Version", "REVIEW" if not version else "INFO", version.group(1) if version else "Could not parse version")
    else:
        add("pubspec.yaml", "BLOCKED", "Not found; choose the Flutter project directory")
    android = project / "android"
    add("Android folder", "PASS" if android.is_dir() else "BLOCKED",
        "Present" if android.is_dir() else "Not found")
    gradle_candidates = [android / "app" / "build.gradle", android / "app" / "build.gradle.kts"]
    add("Android app Gradle config", "PASS" if any(p.is_file() for p in gradle_candidates) else "REVIEW",
        "Found" if any(p.is_file() for p in gradle_candidates) else "Not found in standard locations")
    gitignore = project / ".gitignore"
    add("Git ignore", "PASS" if gitignore.is_file() else "REVIEW",
        "Present" if gitignore.is_file() else "Missing; inspect generated files and secrets")
    # Conservative pattern inventory only; never prints matching lines or values.
    scan_roots = [project / ".env", project / ".env.local", project / "lib", android]
    secret_patterns = [
        re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
        re.compile(r"sk-[A-Za-z0-9]{16,}"),
        re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
    ]
    matches = 0
    scanned = 0
    skipped_large = 0
    read_errors = 0
    for item in scan_roots:
        if not item.exists():
            continue
        files = [item] if item.is_file() else [p for p in item.rglob("*") if p.is_file()]
        for file in files:
            if file.name in {"google-services.json"}:
                # Firebase client configuration is not equivalent to a private server secret.
                continue
            try:
                if file.stat().st_size > 2_000_000:
                    skipped_large += 1
                    continue
                content = file.read_text(encoding="utf-8", errors="ignore")
                scanned += 1
                matches += sum(len(pattern.findall(content)) for pattern in secret_patterns)
            except OSError:
                read_errors += 1
    scan_status = "REVIEW" if matches or skipped_large or read_errors else "INFO"
    add("Common secret-pattern scan", scan_status,
        f"Scanned {scanned} files; skipped oversized files: {skipped_large}; "
        f"file read errors: {read_errors}; potential pattern matches: {matches}. "
        "Not a full secrets scan.")
    add("Signing configuration", "NOT RUN", "Manually verify release signing setup and keep private keys out of source control")
    add("Permissions and privacy", "NOT RUN", "Review Android permissions, privacy policy and actual data practices")
    add("Dependencies and licenses", "NOT RUN", "Run dependency review and complete the asset/license inventory")
    add("Flutter analyze, tests and release build", "NOT RUN", "Run on a configured Flutter environment and record actual command results")
    add("Device smoke test and store compliance", "NOT RUN", "Install the release build and complete the store checklist")
    return {"project": str(project), "read_only": True, "findings": findings,
            "note": "Preflight is a heuristic checklist, not a security audit, build, or Play Store approval."}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    project = args.project.resolve()
    result = inspect(project)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Read-only release preflight:", project)
        for finding in result["findings"]:
            print(f"[{finding['status']}] {finding['check']}: {finding['detail']}")
        print(result["note"])
    return 0 if any(f["check"] == "pubspec.yaml" and f["status"] == "PASS" for f in result["findings"]) else 1

if __name__ == "__main__":
    sys.exit(main())
