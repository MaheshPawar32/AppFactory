# MyAppFactory v1.3 — Quality, safety and release workflow

This release focuses on repeatable multi-app development and safer AI-assisted changes.

## What's included
- Git checkpoint and rollback workflow.
- Continuous integration example for formatting, analysis and tests.
- Architecture guidance for repositories, local storage and remote services.
- Android release checklist and environment/secrets guidance.
- Localization starter guidance for English, Hindi and Marathi.
- UI regression testing guidance and dependency/license review.
- A Claude workflow that requires inspection, small diffs and honest verification reporting.

## Suggested sequence
1. Initialize Git and commit a clean baseline before starting a new feature.
2. Ask Claude to inspect the app and return a plan before editing.
3. Implement one feature at a time and review the diff.
4. Run format, analyze and tests locally or through CI.
5. Build a debug APK; prepare a release AAB only after reviewing signing and privacy requirements.
6. Save the final test/build outputs and release notes alongside the app.

## Important
The included CI workflow is a starter example, not proof that a project has passed CI. Review Flutter version and action versions against your installed toolchain. Firebase and AdMob remain optional and must be explicitly selected per app.
