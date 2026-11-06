# Developer Command Center (v2.0)

Run from the MyAppFactory root:

```bash
python3 scripts/project_dashboard.py
python3 scripts/project_dashboard.py --json
python3 scripts/visual_qa_report.py
python3 scripts/visual_qa_report.py --project /path/to/your/app --json
```

The dashboard reads `apps/PROJECT_REGISTRY.csv`; it does not infer that tests passed because test files or build outputs exist. Add a `project_path` column if you want path visibility. Relative paths are resolved from the MyAppFactory root. Record actual statuses, verification date and next action after executing checks.

Visual QA report checks whether the tracker and device matrix exist and summarizes recorded status counts. It does not inspect screenshot content or claim that a UI is correct. Keep actual per-app trackers in the app project and run with `--project`.

```bash
python3 scripts/release_preflight.py /path/to/flutter/app
python3 scripts/release_preflight.py /path/to/flutter/app --json
```

The release preflight is read-only and heuristic. It flags common setup gaps and reports manual release checks as `NOT RUN`; it is not a complete secrets scanner, Flutter build, security audit or Play Store certification.
