#!/usr/bin/env python3
"""Preview Nova UI source-to-starter changes without overwriting app-specific files."""

from pathlib import Path
import argparse
import difflib
import sys
from template_sync import compare_files

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "design_system" / "nova_ui_flutter"
TARGET = ROOT / "templates" / "nova_ui_flutter_starter"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--show-diff",
        action="store_true",
        help="Print unified diffs for changed text files",
    )
    args = parser.parse_args()

    if not SOURCE.is_dir() or not TARGET.is_dir():
        print("ERROR: source or starter template is missing.")
        return 2

    comparison = compare_files(SOURCE, TARGET)
    src = comparison["source_files"]
    dst = comparison["target_files"]
    missing = comparison["missing"]
    extra = comparison["extra"]
    changed = comparison["different"]

    print("Nova UI template update preview (read-only)")
    print(f"Source files: {len(src)} | Template files: {len(dst)}")
    print(f"\nNew in source / missing in template: {len(missing)}")
    for name in missing:
        print(f"  {name}")

    print(f"\nExtra in template: {len(extra)}")
    for name in extra:
        print(f"  {name}")

    print(f"\nChanged files: {len(changed)}")
    for name in changed:
        print(f"  {name}")

    if args.show_diff:
        for name in changed:
            try:
                source_text = src[name].read_text(encoding="utf-8").splitlines(True)
                target_text = dst[name].read_text(encoding="utf-8").splitlines(True)
            except UnicodeDecodeError:
                print(f"\n[Binary file; diff omitted: {name}]")
                continue

            print("".join(difflib.unified_diff(
                target_text,
                source_text,
                fromfile=f"template/{name}",
                tofile=f"source/{name}",
            )))

    print("\nNo files were changed. This preview is read-only.")
    return 1 if missing or extra or changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
