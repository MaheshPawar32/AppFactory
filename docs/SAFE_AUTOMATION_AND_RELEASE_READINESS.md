# Safe Automation and Release Readiness (v2.1)

## Principle
Automation may prepare and inspect. It must not silently publish, sign, upload, delete, migrate production data, or change external account settings.

## Release readiness gates
- [ ] Correct package/application ID and version.
- [ ] App icon, display name, supported SDK configuration and permissions reviewed.
- [ ] No known credentials committed; inspect `.env`, config files, generated files and Git history as appropriate.
- [ ] Release signing configuration is present locally and private signing files are excluded from source control.
- [ ] Privacy policy, Data safety answers, target audience, content rating, ads declarations and store assets reviewed for the actual app.
- [ ] Dependency review and license inventory completed.
- [ ] Offline, error, permission-denied and critical journey tests completed.
- [ ] `flutter analyze`, `flutter test` and release build run on a Flutter-enabled machine; record exact outcomes.
- [ ] Install and smoke-test the release build on a real device or emulator.
- [ ] Versioned release record and rollback/incident contact prepared.

## Safety modes
- `preview`: read-only report, no changes.
- `prepare`: generate local artifacts or checklists; no external submission.
- `execute`: only a clearly described, explicitly approved operation; show target and consequences before acting.
- Any missing credential, uncertain target, dirty-worktree risk or failed precondition should stop the operation.

## Status vocabulary
`PASS` = executed and passed; `FAIL` = executed and failed; `BLOCKED` = cannot run due to a known blocker; `NOT RUN` = not attempted; `REVIEW` = requires human judgement. Presence of a file or checklist is not a pass.
