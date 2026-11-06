# MyAppFactory v2.3 — App Creation and Configuration Reliability

## Added
- Read-only `scripts/validate_flutter_project.py` checks common Flutter/Android scaffolding, Gradle package metadata, manifest flags, permissions inventory and expected folders.
- Findings are labeled as PASS, FAIL, REVIEW, INFO or NOT RUN; simple text matching is not treated as proof.
- The validator does not create platform files, modify application IDs, run Flutter, or make release decisions.

## Usage
```bash
python3 scripts/validate_flutter_project.py path/to/flutter_app
python3 scripts/validate_flutter_project.py path/to/flutter_app --json
```

## Safe repair policy
Back up or commit the project before changing Android scaffolding. If `android/` is missing, inspect `flutter create .` output before accepting changes. Confirm `applicationId`, namespace, package name, Firebase configuration and Play Console identity together before release.
