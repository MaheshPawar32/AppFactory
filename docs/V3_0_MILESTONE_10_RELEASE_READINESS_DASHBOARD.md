# MyAppFactory v3.0 — Milestone 10: Release Readiness Dashboard

## Purpose
Combines registry statuses, discovered factory build-engine reports, and artifact-index records into one JSON/HTML overview for registered Flutter projects.

## Generate a dashboard
```bash
python3 scripts/release_readiness_dashboard.py
python3 scripts/release_readiness_dashboard.py --json reports/release_readiness.json --html reports/release_readiness.html
```
The dashboard is read-only with respect to app projects and the registry. It writes only the report files you specify. Relative project paths are resolved against `--base` (defaults to MyAppFactory).

## Evidence rules
- Registry statuses are displayed as recorded claims; they are not treated as fresh proof.
- Build-engine reports are discovered from `build/factory_runs/` and `build/factory_batch_runs/`.
- Artifact records are included only when their indexed file paths still exist on disk.
- A passing report with an existing indexed artifact is labelled `REVIEW REQUIRED`, never “ready to publish”.
- Missing paths/manifests are `BLOCKED`; absent evidence is `NOT VERIFIED`.
- Signature status and publication status remain explicit, and are not inferred from file presence.

## Limits
This is an evidence summary, not a signing verifier, install test, security audit, privacy review, or Play Store policy assessment. It does not build, sign, upload, or publish apps.
