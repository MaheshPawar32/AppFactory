# MyAppFactory v3.0 — Milestone 5: Reusable App Runtime Kit

## Included
- Dependency-free Dart `AppResult<T>` / `AppFailure` primitives.
- Immutable `AsyncState<T>` with idle, loading, data, error, and optional previous data.
- `SafeAction` to prevent concurrent duplicate invocation.
- Conservative installer that targets `lib/core/runtime/`, validates `pubspec.yaml`, refuses collisions by default, and does not change dependencies.
- Acceptance notes and integration guidance.

## Install into an existing app
From the MyAppFactory root:

```bash
python3 scripts/install_runtime_kit.py /path/to/flutter_app --json
```

The installer copies source files only. It does not edit `pubspec.yaml`, imports, routing, Provider setup, or screens. Review copied files and connect them intentionally. If a filename conflict occurs, inspect the existing file before deciding whether `--overwrite` is appropriate.

## Recommended use
- Use `AppResult<T>` for expected success/failure outcomes at repository or service boundaries.
- Use `AsyncState<T>` for screen/request state while preserving previous data during refresh.
- Use `SafeAction` for actions where a second simultaneous submit must be ignored.
- Keep error messages user-safe and diagnostics separate from UI messages.
- Preserve the app's current state management and Nova UI components.

## Required validation in the target app
Run `dart format`, `flutter analyze`, focused unit/widget tests, `flutter test`, and Android device checks. The runtime kit is dependency-free but has not been compiled with Flutter in this build environment. The installer is not a migration tool and does not automatically integrate the primitives into screens.
