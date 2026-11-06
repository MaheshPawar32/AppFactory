# Offline-first local storage

Persist user-owned data on device with explicit schema/versioning and export/clear behavior.

## Dependency policy

This recipe does not add dependencies automatically. Review the target app's existing `pubspec.yaml`, SDK constraints, state management, and architecture first. Add only the selected package(s), pin compatible versions through normal Pub resolution, and record the decision in `DEPENDENCY_REVIEW.md`.

## Available choices

- `hive`
- `shared_preferences`
- `sqflite`
- `isar`

## Acceptance checks

- [ ] Choose one storage engine based on data shape; do not add multiple engines without justification.
- [ ] Version and migrate persisted schemas; preserve existing user data.
- [ ] Include empty/loading/error states and safe clear/export behavior where appropriate.
- [ ] Test persistence across app restarts and malformed/old data recovery.
