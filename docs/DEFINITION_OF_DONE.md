# Definition of Done — every app

A feature or app is not complete merely because code was generated.

## Product and UX
- [ ] Every agreed screen is implemented.
- [ ] Every visible action works or is explicitly labelled as unavailable/not in scope.
- [ ] No dead buttons, fake success messages or unexplained placeholders.
- [ ] Loading, empty, error, offline, permission-denied and success states exist where relevant.
- [ ] Android back navigation, keyboard behavior and accessibility are reviewed.
- [ ] UI references have been compared against rendered output when tooling is available.

## Data and integrations
- [ ] Data persists as specified and survives restart where expected.
- [ ] Validation, duplicate submission prevention and recoverable errors are handled.
- [ ] Integrations are marked `not configured`, `configured`, `tested`, or `not applicable`.
- [ ] Secrets and signing credentials are not committed.
- [ ] Data export/deletion and privacy behavior are documented where relevant.

## Verification
- [ ] Formatting check result recorded.
- [ ] Static analysis result recorded.
- [ ] Unit/widget test result recorded.
- [ ] Integration test result recorded or marked not run/not applicable with reason.
- [ ] Debug build result recorded.
- [ ] Known issues and manual checks listed.

## Release readiness
- [ ] App ID, version, permissions, icon and splash screen reviewed.
- [ ] Generated Android flavor and Dart environment values match; no client build contains server secrets.
- [ ] APP_CONFIG is validated and its architecture audit status is recorded honestly (including `PARTIAL` when layer rules were not exercised).
- [ ] Store artwork and screenshots are supplied or explicitly marked not provided/not captured.
- [ ] Privacy policy and Play Console declarations reviewed where applicable.
- [ ] Release signing configuration verified securely.
- [ ] Release AAB generated and inspected if release was requested.
- [ ] Real-device testing and publishing status are reported truthfully.

## Required completion report
1. Implemented features.
2. Incomplete or intentionally excluded features.
3. Files changed.
4. Commands actually run and their results.
5. Build artifact paths, only if created and verified.
6. Known issues and next steps.
