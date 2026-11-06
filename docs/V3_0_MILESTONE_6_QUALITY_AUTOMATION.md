# MyAppFactory v3.0 — Milestone 6: Quality Automation

## New tools
- `scripts/dependency_compatibility_review.py`: read-only `pubspec.yaml` review. It identifies declared dependencies, SDK constraint and common review flags. It does not query pub.dev or guarantee version compatibility.
- `scripts/change_impact_report.py`: maps Git changes or an explicit file list to recommended test/review areas.
- `scripts/release_readiness_preflight.py`: validates basic project structure and optionally runs format, analyze and tests. It never builds/signs/uploads/publishes.

## Examples

```bash
python3 scripts/dependency_compatibility_review.py apps/my_app --json
python3 scripts/change_impact_report.py apps/my_app --json --output apps/my_app/CHANGE_IMPACT.json
python3 scripts/change_impact_report.py apps/my_app --files lib/home.dart pubspec.yaml --json
python3 scripts/release_readiness_preflight.py apps/my_app --json
python3 scripts/release_readiness_preflight.py apps/my_app --run-flutter-checks --json
```

## Interpretation
- Dependency review is a static review, not a remote package compatibility guarantee. Run `flutter pub get` and inspect the resolved lockfile in the target environment.
- Change impact recommendations are heuristics; always inspect the actual diff and add tests for behavior not detected by path names.
- Release preflight is a readiness aid, not a Play Console compliance certification. Device, signing, privacy, consent, permission, and store-listing checks remain human responsibilities.
- Optional Flutter checks can be BLOCKED if the Flutter/Dart tools are unavailable. Commands are not claimed to pass unless the report says PASS.
