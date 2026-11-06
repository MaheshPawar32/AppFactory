# MyAppFactory v3.0 — Milestone 11: Regression & Device QA Orchestrator

## Overview
Coordinates the existing Visual QA runner across projects in `apps/PROJECT_REGISTRY.csv`. It supports dry-run previews, Flutter tests, optional manifest-defined commands, and optional Android screen capture.

## Dry-run
```bash
python3 scripts/device_qa_orchestrator.py
python3 scripts/device_qa_orchestrator.py --app "BodyStats"
```
Dry-run is the default and does not execute app tests or capture screens.

## Execute tests
```bash
python3 scripts/device_qa_orchestrator.py --execute
```
For a selected app:
```bash
python3 scripts/device_qa_orchestrator.py --app "BodyStats" --execute
```

## Optional screenshot capture
```bash
python3 scripts/device_qa_orchestrator.py --app "BodyStats" --execute --capture --device emulator-5554 --manifest /path/to/VISUAL_QA_MANIFEST.json
```
Start and unlock the emulator/device and manually navigate to the requested UI state before capture. This tool does not tap, navigate, or automatically drive app screens. Avoid personal notifications, account details and secrets in screenshots.

## Outputs
- Summary JSON defaults to `reports/device_qa_summary.json`.
- Per-app reports and screenshots default to `reports/device_qa_runs/<app>/`.
- Override output locations with `--output` and `--output-root`.

## Safety and interpretation
- `--execute` is required to run the QA runner; the default is dry-run.
- `--skip-tests` omits the runner's default `flutter test`; manifest test commands still run if supplied.
- Connected device capture requires adb and a manually prepared screen state.
- Reports do not prove visual correctness, device compatibility, signing, store compliance or release readiness.
- The orchestrator does not update the registry, generate source, sign, upload or publish apps.
