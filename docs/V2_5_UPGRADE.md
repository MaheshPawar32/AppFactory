# MyAppFactory v2.5 — One-Command Factory Checks and Release Guardrails

## Added
- `scripts/run_factory_checks.py` runs the factory's standard-library and structural checks and emits a JSON report.
- The runner is read-only with respect to app source, does not run a release build, and has an opt-in strict exit code.
- New upgrade docs summarize safe setup, visual evidence and release readiness.

## Usage
```bash
python3 scripts/run_factory_checks.py
python3 scripts/run_factory_checks.py --strict
python3 scripts/run_factory_checks.py --report reports/factory-checks.json --strict
```

The report is a record of the commands actually run. It does not replace `flutter pub get`, `dart format`, `flutter analyze`, `flutter test`, `flutter build apk --release`, device installation, privacy review, signing verification or Play Console checks.

## Release evidence to capture per app
- Git commit and app version
- Flutter and Dart versions
- dependency resolution result
- formatter, analyzer and test outputs
- release build command and exit status
- device smoke test and visual QA evidence
- permissions, privacy, signing, asset/license and store policy review
- known issues and rollback plan

Never put signing keys, service account keys, API secrets or real user data into reports.
