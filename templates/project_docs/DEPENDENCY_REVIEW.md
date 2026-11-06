# Dependency Review

- App:
- Review date:
- Flutter / Dart versions:

## Static review
- [ ] Review direct dependencies and why each is needed.
- [ ] Review `dependency_overrides`.
- [ ] Review Git/path dependencies and pinned revisions.
- [ ] Confirm `pubspec.lock` is committed for the app.
- [ ] Review Android permissions against actual features.
- [ ] Review licenses and maintenance status.
- [ ] Check secrets and sensitive logging.
- [ ] Run `python3 scripts/dependency_audit.py <app-folder>`.
- [ ] If Flutter is installed, run `flutter pub outdated` and review the output.

## Findings
| Severity | Package / file | Finding | Action | Status |
|---|---|---|---|---|

This checklist does not substitute for a CVE scanner, license review or security assessment.
