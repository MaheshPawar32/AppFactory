#!/usr/bin/env python3
"""Install MyAppFactory's dependency-free Dart runtime kit into an existing Flutter app."""
from __future__ import annotations
import argparse, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "templates" / "flutter_runtime_kit" / "lib"

def install(target: Path, overwrite: bool = False):
    target = target.resolve()
    if not (target / "pubspec.yaml").is_file():
        raise ValueError(f"Target is not a Flutter project (pubspec.yaml missing): {target}")
    files = sorted(SOURCE.rglob("*.dart"))
    if not files:
        raise ValueError("Runtime kit source files are missing")
    planned = [(f, target / "lib" / "core" / "runtime" / f.relative_to(SOURCE)) for f in files]
    conflicts = [str(dst) for _, dst in planned if dst.exists() and not overwrite]
    if conflicts:
        raise FileExistsError("Refusing to overwrite existing files; use --overwrite only after reviewing: " + ", ".join(conflicts))
    copied = []
    for src, dst in planned:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(str(dst.relative_to(target)))
    return {"target": str(target), "copied": copied, "overwritten": overwrite, "dependencies_added": []}

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("flutter_project", type=Path)
    p.add_argument("--overwrite", action="store_true", help="Allow replacing colliding files (review first)")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    try:
        result = install(a.flutter_project, a.overwrite)
    except (ValueError, FileExistsError, OSError) as e:
        print(json.dumps({"status": "BLOCKED", "error": str(e)}, indent=2) if a.json else f"BLOCKED: {e}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "COPIED", **result}, indent=2) if a.json else
          "Copied runtime kit files:\n" + "\n".join(result["copied"]) + "\nNo dependencies were added.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
