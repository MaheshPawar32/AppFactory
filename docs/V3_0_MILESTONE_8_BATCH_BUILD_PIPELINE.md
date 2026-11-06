# MyAppFactory v3.0 — Milestone 8: Batch Build Pipeline

## What it does
Runs the existing Flutter build engine for selected apps listed in `apps/PROJECT_REGISTRY.csv`. It validates project paths, creates per-app reports, and supports explicit opt-in registry updates.

## Dry-run first
```bash
python3 scripts/batch_build_pipeline.py
python3 scripts/batch_build_pipeline.py --app "BodyStats" --build none
```
Default mode is dry-run. It does not execute Flutter commands. Update registry rows with real names and project paths first.

## Execute quality checks
```bash
python3 scripts/batch_build_pipeline.py --execute --build none --fix-mode none
```
This runs dependency resolution, format check, analyzer and tests using the existing engine. It does not build an APK/AAB unless explicitly selected.

## Build an artifact explicitly
```bash
python3 scripts/batch_build_pipeline.py --app "My App" --execute --build apk --fix-mode none
python3 scripts/batch_build_pipeline.py --app "My App" --execute --build appbundle --fix-mode none
```

## Optional evidence and registry update
```bash
python3 scripts/batch_build_pipeline.py --execute --build none --update-registry
```
Registry updates are never automatic; `--update-registry` requires `--execute`. Reports default to `reports/batch_build_report.json`; engine logs/reports are stored under each app's `build/factory_batch_runs/` folder unless `--run-output-dir` is supplied.

## Safety boundaries
- Default is dry-run; build artifact defaults to `none`; format fix mode defaults to `none`.
- The pipeline does not generate code, modify signing, invent credentials, upload or publish apps.
- `--fix-mode safe` can run `dart format .` and modify Dart files; use only after reviewing Git status.
- Actual execution requires Flutter/Dart/Android tooling and may update lockfiles during dependency resolution.
- A build-engine PASS is local evidence, not proof of device QA or store compliance.
