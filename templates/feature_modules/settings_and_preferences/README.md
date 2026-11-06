# Settings and preferences

Provide a predictable place for theme, reminders, privacy, data management and app information.

## Dependency policy

This recipe does not add dependencies automatically. Review the target app's existing `pubspec.yaml`, SDK constraints, state management, and architecture first. Add only the selected package(s), pin compatible versions through normal Pub resolution, and record the decision in `DEPENDENCY_REVIEW.md`.

## Available choices

- `theme`
- `reminders`
- `privacy`
- `data_management`
- `about`

## Acceptance checks

- [ ] Settings reflect actual app state and persist across restarts when appropriate.
- [ ] Use accessible labels, confirmation for destructive actions, and a clear reset path.
- [ ] Do not display settings for integrations that are not configured.
- [ ] Test persistence, reset behavior, and permission-state changes.
