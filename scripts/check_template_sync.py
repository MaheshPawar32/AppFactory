#!/usr/bin/env python3
"""Compare only intentional reusable Nova UI starter files."""

from pathlib import Path
import sys
from template_sync import compare_files

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "design_system" / "nova_ui_flutter"
TARGET = ROOT / "templates" / "nova_ui_flutter_starter"
if not SOURCE.is_dir() or not TARGET.is_dir():
    print("Template sync check FAILED: source or starter template is missing")
    sys.exit(1)

comparison = compare_files(SOURCE, TARGET)
source_files = comparison["source_files"]
target_files = comparison["target_files"]
missing = comparison["missing"]
extra = comparison["extra"]
different = comparison["different"]

if missing or extra or different:
    print("Template sync check FAILED")

    if missing:
        print("Missing from template:", *missing, sep="\n  ")

    if extra:
        print("Extra in template:", *extra, sep="\n  ")

    if different:
        print("Different files:", *different, sep="\n  ")

    sys.exit(1)

print(f"Template sync check PASSED ({len(source_files)} files compared)")
