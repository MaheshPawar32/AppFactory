# Local notifications

Schedule on-device reminders with user controls and timezone-aware behavior.

## Dependency policy

This recipe does not add dependencies automatically. Review the target app's existing `pubspec.yaml`, SDK constraints, state management, and architecture first. Add only the selected package(s), pin compatible versions through normal Pub resolution, and record the decision in `DEPENDENCY_REVIEW.md`.

## Available choices

- `daily_reminders`
- `scheduled_reminders`
- `streak_reminders`

## Acceptance checks

- [ ] Ask notification permission contextually and respect denial without blocking the app.
- [ ] Use stable notification IDs; cancel or reschedule obsolete reminders.
- [ ] Handle Android notification channel and exact-alarm requirements only when needed.
- [ ] Test permission denied, app restart, timezone/daylight changes, and duplicate scheduling.
