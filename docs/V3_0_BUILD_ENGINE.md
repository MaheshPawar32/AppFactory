# MyAppFactory v3.0 — Build and Recovery Engine (Milestone 1)

## Goal
Turn MyAppFactory from a set of helpful scripts and prompts into a repeatable app production workflow. Milestone 1 provides a real command runner for a Flutter project that already has `pubspec.yaml`.

## Run
From the MyAppFactory folder:
```bash
python3 scripts/flutter_build_engine.py /absolute/path/to/flutter_app --build apk
python3 scripts/flutter_build_engine.py /absolute/path/to/flutter_app --build appbundle
python3 scripts/flutter_build_engine.py /absolute/path/to/flutter_app --build none
python3 scripts/flutter_build_engine.py /absolute/path/to/flutter_app --dry-run
```

Generated apps with Android product flavors can select one for the artifact
build and pass compile-time configuration explicitly:
```bash
python3 scripts/flutter_build_engine.py /absolute/path/to/flutter_app \
  --build apk --flavor development --dart-define APP_ENV=development
```
Repeat `--dart-define KEY=VALUE` for additional non-secret values. Do not pass
server secrets to client builds. `--flavor` and Dart defines apply only to the
artifact build step; dependency resolution, formatting, analysis and tests are
still run as project-wide checks. Use `--dry-run` to inspect the exact command.

The engine checks Flutter availability, resolves dependencies, checks Dart formatting, analyzes code, runs tests (unless skipped), and optionally builds a release APK or AAB. It records command output and a JSON report under the target project's `build/factory_runs/<run_id>/` directory by default.

## Recovery behavior
- `flutter pub get`: retry once by default.
- Formatting check: with `--fix-mode safe`, run `dart format .` once, then re-check. This modifies Dart formatting; review the Git diff.
- Analyzer and test failures: stop and report; do not rewrite application code.
- Release build: retry once after a fresh `flutter pub get`; does not run `flutter clean` or delete files.
- Retry count is bounded and configurable with `--max-retries 0|1|2`.

## Safety
- The engine never generates source code, changes app IDs, configures signing, invents secrets, commits/stashes changes, or publishes to a store.
- It captures a read-only Git working-tree snapshot before and after when Git is available.
- Use a clean Git commit or backup before allowing safe formatting changes.
- Review logs/reports before accepting changes. Build success does not guarantee correct behavior, store approval or secure signing.

## Requirements
Python 3.9+ and a configured Flutter SDK are recommended. Release builds additionally require the Android SDK/toolchain and suitable project configuration. If Flutter is missing, the engine exits as BLOCKED and reports why.
