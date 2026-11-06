# Safe Claude workflow

## Before editing
- Inspect `pubspec.yaml`, project structure, routes, state management, models, persistence and existing tests.
- Identify whether this is a new or existing app.
- Summarize current behavior, planned files and risk before changing code.
- Never replace the whole project just to add a feature.

## During implementation
- Prefer small, reviewable edits.
- Preserve existing architecture and user data.
- Do not add packages without explaining why and checking compatibility.
- Do not change package name, signing, permissions, Firebase configuration or production ad IDs without approval.
- Keep secrets out of Git and logs.
- Add tests for new behavior and update docs where behavior changes.

## Before reporting completion
- Show the changed-file summary.
- Report the exact commands actually run and their results.
- Distinguish not-run, failed and passed checks.
- List known limitations and manual checks still needed.
- Do not claim the app was installed, published, or tested on a device unless that actually happened.

## Git checkpoint example
```bash
git status
git add .
git commit -m "chore: checkpoint before feature work"
```

## Rollback guidance
Review `git diff` before committing. If a change is wrong, prefer a targeted revert or restore of only the affected files. Do not use destructive reset/clean commands unless the user explicitly approves and understands the data loss.
