#!/usr/bin/env python3
"""MyAppFactory V7 command line. Run `python3 scripts/factory.py --help`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from myappfactory.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
