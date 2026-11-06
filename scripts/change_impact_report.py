#!/usr/bin/env python3
"""Create a deterministic change-impact checklist from Git diff metadata."""
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

RULES = [
    (("pubspec.yaml", "pubspec.lock"), "dependencies", ["dependency review", "pub get", "analyze", "focused tests"]),
    (("lib/", "test/"), "dart_code", ["format", "analyze", "unit/widget tests", "affected-screen regression"]),
    (("android/", "ios/"), "platform", ["platform build", "permissions/configuration review", "device smoke test"]),
    (("assets/", "fonts/"), "assets", ["asset path/license review", "missing-asset check", "visual review"]),
    (("l10n/", "arb", "localization"), "localization", ["translation-key review", "long-text/RTL review", "locale smoke test"]),
    (("firebase", "google-services", "GoogleService-Info"), "firebase", ["configuration/privacy review", "security rules review", "runtime integration test"]),
    ((".github/", "scripts/", "docs/"), "tooling_docs", ["workflow/script validation", "documentation review"]),
]
def classify(path):
    normalized = path.replace("\\", "/")
    return [ {"area": area, "checks": checks} for tokens, area, checks in RULES if any(t in normalized for t in tokens) ]

def git_changed_files(project: Path, base: str | None, staged: bool = False):
    if staged:
        cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
    elif base:
        cmd = ["git", "diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD"]
    else:
        cmd = ["git", "diff", "--name-only", "--diff-filter=ACMR", "HEAD"]
        # Include untracked files as potential change candidates.
        untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=project, text=True, capture_output=True)
        if untracked.returncode == 0:
            extra = [x for x in untracked.stdout.splitlines() if x]
        else:
            extra = []
    p = subprocess.run(cmd, cwd=project, text=True, capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or "git diff failed")
    files = [x for x in p.stdout.splitlines() if x]
    if not staged and not base:
        files.extend(extra)
    return sorted(set(files))

def build_report(files):
    report = []
    for path in sorted(set(files)):
        categories = classify(path)
        report.append({"path": path, "areas": categories or [{"area": "general", "checks": ["review diff", "run relevant tests"]}]})
    checks = sorted({check for item in report for area in item["areas"] for check in area["checks"]})
    return {"schema_version": 1, "changed_file_count": len(report), "files": report, "recommended_checks": checks}

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("project", type=Path, nargs="?", default=Path.cwd())
    p.add_argument("--base", help="Compare current HEAD to a base ref, e.g. origin/main")
    p.add_argument("--staged", action="store_true", help="Inspect staged changes only")
    p.add_argument("--files", nargs="*", help="Classify an explicit file list instead of reading Git")
    p.add_argument("--output", type=Path)
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    project = a.project.resolve()
    try:
        files = a.files if a.files is not None else git_changed_files(project, a.base, a.staged)
        report = build_report(files)
    except (RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(report, indent=2)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered if a.json or not a.output else f"Change impact report written to {a.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
