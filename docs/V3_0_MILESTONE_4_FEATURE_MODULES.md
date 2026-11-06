# MyAppFactory v3.0 — Milestone 4: Reusable Feature Modules

## Goal
Provide a controlled, opt-in catalog of reusable feature recipes and a small CLI that validates selections and creates a focused Claude Code implementation brief. This milestone intentionally does not bulk-copy code or add packages to apps automatically.

## Included modules
- Offline storage (Hive, SharedPreferences, SQLite/sqflite, or Isar choice)
- Local notifications
- First-run onboarding
- Settings and preferences
- Forms and validation
- HTTP API client
- Optional Firebase services
- Optional AdMob monetization

Each module has a machine-readable `module.json`, implementation guidance, dependency review reminders, and acceptance criteria. `templates/project_docs/FEATURE_MODULES.json` is an editable example manifest.

## Workflow
From the factory root:

```bash
python3 scripts/feature_module_manager.py list
python3 scripts/feature_module_manager.py validate templates/project_docs/FEATURE_MODULES.json
python3 scripts/feature_module_manager.py prompt templates/project_docs/FEATURE_MODULES.json --output apps/your_app/FEATURE_MODULE_IMPLEMENTATION_PROMPT.md
```

Edit the example manifest first. Set the app path and select only modules the app needs. The generated prompt can be pasted into Claude Code from the target app folder.

## Status and evidence
Allowed statuses: `not configured`, `configured`, `tested`, `not applicable`. A `tested` status requires an evidence field. Optional Firebase/AdMob modules need `approved: true` to avoid a warning when marked configured. Status is a record, not proof; keep evidence truthful.

## Safety boundaries
- The manager validates choices and generates a prompt; it does not write app source, install packages, configure Firebase, publish apps, or run Flutter builds.
- Review current project architecture and Git status before implementation.
- Keep the existing state-management framework. Do not add a second one for forms or settings.
- Do not add multiple local storage or HTTP engines without a documented reason.
- Never commit credentials, service configuration files, or production ad IDs.
- Run `flutter pub get`, `dart format --set-exit-if-changed .`, `flutter analyze`, `flutter test`, and relevant Android device tests in the actual Flutter environment.
