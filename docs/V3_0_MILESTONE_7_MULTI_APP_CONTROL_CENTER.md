# MyAppFactory v3.0 — Milestone 7: Multi-App Control Center

## Goal
A read-only, multi-project overview that turns `apps/PROJECT_REGISTRY.csv` into a JSON report or standalone responsive HTML dashboard.

## Registry
The CSV tracks app name, package, version, platform, project path, recorded analyzer/test/build statuses, blockers, next action, last checked time, and evidence path. Existing rows are preserved when upgrading the header; fill in real app data and real check results.

Allowed check statuses include `PASS`, `FAIL`, `BLOCKED`, `WARN`, `NOT RUN`, `UNKNOWN`, `IN PROGRESS`, and `PLANNED`.

## Usage

```bash
python3 scripts/multi_app_control_center.py --json
python3 scripts/multi_app_control_center.py --html reports/control_center.html
python3 scripts/multi_app_control_center.py --json --output reports/control_center.json --html reports/control_center.html
```

Open the generated HTML file in a browser. It is a static report with no server or JavaScript dependencies.

## Safety and accuracy
- The dashboard reads registry values and checks whether recorded project paths exist. It does not execute app code, run tests, build artifacts, or validate a recorded PASS.
- `RECORDED PASS` means the registry says the checks passed; rerun checks after changes.
- Empty or stale registry fields should be updated manually with timestamps and evidence paths.
- Do not put secrets, tokens, or private user data in registry notes.
