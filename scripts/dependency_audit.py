\
#!/usr/bin/env python3
"""Static dependency-risk inventory for pubspec.yaml; does not query package registries."""
from pathlib import Path
import argparse, re, shutil, subprocess, sys

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".", help="Flutter project directory")
    parser.add_argument("--pub-outdated", action="store_true", help="Run flutter pub outdated if Flutter is installed")
    args=parser.parse_args()
    project=Path(args.project).resolve()
    pubspec=project/"pubspec.yaml"
    if not pubspec.is_file():
        print(f"ERROR: {pubspec} not found"); return 2
    text=pubspec.read_text(encoding="utf-8")
    findings=[]
    if re.search(r"(?m)^dependency_overrides\s*:", text):
        findings.append(("REVIEW","dependency_overrides exists; confirm it is temporary and necessary"))
    if re.search(r"(?m)^\s+(git|path)\s*:", text):
        findings.append(("REVIEW","Git/path dependency found; verify source trust, reproducibility and local portability"))
    if re.search(r"(?m)^\s+[A-Za-z0-9_]+\s*:\s*(any|latest)\s*(?:#.*)?$", text):
        findings.append(("REVIEW","A dependency uses 'any' or 'latest'; prefer an intentional constraint"))
    if re.search(r"(?m)^\s+http\s*:", text) and not re.search(r"(?m)^\s+https\s*:", text):
        findings.append(("REVIEW","Inspect dependency sources for insecure HTTP endpoints"))
    if not findings: findings.append(("INFO","No configured static-risk patterns found; this is not a vulnerability scan"))
    print(f"Static dependency review: {pubspec}")
    for level,msg in findings: print(f"[{level}] {msg}")
    if args.pub_outdated:
        flutter=shutil.which("flutter")
        if not flutter:
            print("[NOT RUN] flutter pub outdated: Flutter executable not found")
        else:
            result=subprocess.run([flutter,"pub","outdated"],cwd=project,text=True)
            print(f"flutter pub outdated exit code: {result.returncode}")
            return result.returncode
    print("Latest versions, known CVEs, license suitability and transitive dependency risks were not checked.")
    return 0
if __name__=="__main__": raise SystemExit(main())
