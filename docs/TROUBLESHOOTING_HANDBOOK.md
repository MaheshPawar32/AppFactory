# Flutter / Android Troubleshooting Handbook

This is a triage guide, not a guarantee that a fix applies to every SDK version. Capture the complete first error and environment versions before changing files.

## Start with evidence
- Record `flutter --version`, `dart --version`, Java version and the Android Gradle Plugin / Gradle versions used by the project.
- Run `flutter doctor -v`.
- Read the first meaningful error in the build output; later errors may be cascading failures.
- When Git metadata is available, check `git status` and make a commit/backup before changing Gradle, lockfiles or generated configuration. If Git is unavailable, preserve a separate backup and record that version-control status could not be inspected.

## Common categories
- **Package resolution:** inspect `pubspec.yaml` constraints and `pubspec.lock`; run `flutter pub get`. Do not delete the lockfile as a first step.
- **Analyzer / format:** run `dart format lib test` and `flutter analyze`; fix the underlying issue rather than hiding diagnostics globally.
- **Gradle / Java mismatch:** compare the project's Gradle wrapper, Android Gradle Plugin and JDK requirements. Upgrade as a compatible set and consult release notes for the exact versions.
- **Generated app flavor not selected:** app creator projects define `development`, `staging` and `production` variants. Pass `--flavor <name>` to Flutter build/run and pair it with the matching `--dart-define=APP_ENV=<name>`. Do not change the production application ID to resolve a development install conflict.
- **Android SDK / licenses:** use `flutter doctor -v`; install the required SDK components and accept licenses only on the developer's machine.
- **Firebase setup:** confirm the correct Firebase project and Android application ID; regenerate platform configuration only when project identity is confirmed. Never paste service account private keys into source control.
- **AdMob setup:** confirm the correct app ID and ad-unit IDs, test with test ads, follow current Google Mobile Ads guidance and verify consent/privacy requirements for target regions. Do not use real ad traffic for testing.
- **Signing / release:** keep keystore and passwords outside Git; verify release signing configuration locally. Do not send signing secrets to an AI assistant.
- **Runtime crash:** collect stack trace, device/OS, reproduction steps and relevant redacted logs; do not include tokens or personal user data.
- **Network/API failure:** distinguish DNS, TLS, HTTP status, timeout, authorization and server errors; never log access tokens.

## Safe recovery sequence
1. Save the failing output and current Git diff.
2. Reproduce with the exact command.
3. Check version compatibility and project-specific documentation.
4. Make one minimal change.
5. Re-run the failing command and relevant tests.
6. Record outcome and rollback steps.

Avoid blanket cache deletion, arbitrary version upgrades, disabling TLS, suppressing warnings, or replacing configuration files without understanding the impact.
