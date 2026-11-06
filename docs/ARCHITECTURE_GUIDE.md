# Reusable app architecture

Use a feature-first structure that fits the size of the app. Do not add layers just for ceremony.

```text
lib/
  app/
    app.dart
    router.dart
    app_config.dart
  core/
    design_system/
    errors/
    network/
    storage/
    utils/
  features/
    feature_name/
      data/
        models/
        repositories/
        sources/
      domain/        # optional for complex business rules
      presentation/
        screens/
        widgets/
        state/
```

## Repository contract
- Screens/widgets depend on a repository interface or a clear service boundary, not directly on a database SDK everywhere.
- Local and remote implementations can be swapped where it adds real value.
- Keep serialization and migrations explicit.
- Use typed error states; do not silently swallow exceptions.
- Keep state management consistent with the existing project. Provider is the default only for new projects in this factory; preserve the architecture of existing projects.

## Storage choice
- Small preferences: shared preferences or an equivalent simple key/value store.
- Structured offline records and queries: evaluate SQLite/Drift or Hive based on query and migration needs.
- Remote sync/auth: select Firebase, Supabase or a custom API only after requirements are known.
- Never add a database or state-management package automatically without considering app needs.

## Network and offline behavior
- Define loading, data, empty, error, and offline states.
- Preserve user input after recoverable failures.
- Add retry and timeout behavior where appropriate.
- Prevent duplicate submissions.
- For sync, define conflict resolution and retry policy before coding.

## Configuration
- Keep development/staging/production values separate.
- Commit `.env.example` with placeholders only, never real secrets.
- Client-side environment variables are not a safe place for server secrets.
- For static feature-layer import-boundary checks, run `python3 scripts/architecture_audit.py /path/to/flutter-app`.
  The audit only checks recognized Dart imports; it does not replace design review.
