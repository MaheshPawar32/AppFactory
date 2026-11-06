# Standard project deliverables

Each generated app should include these files where applicable:

```text
apps/<app_name>/
  README.md
  docs/
    APP_BRIEF.md
    SCREEN_INVENTORY.md
    ARCHITECTURE.md
    SETUP.md
    TEST_REPORT.md
    KNOWN_ISSUES.md
    RELEASE_CHECKLIST.md
  lib/
  test/
  integration_test/   # when end-to-end tests are implemented
```

## Required documentation content
- README: purpose, requirements, install/run commands and feature summary.
- APP_BRIEF: target users, scope, decisions and assumptions.
- SCREEN_INVENTORY: all screens, navigation, actions and states.
- ARCHITECTURE: state management, storage, services and data flow.
- SETUP: required tools, configuration and optional integrations.
- TEST_REPORT: commands actually run, timestamp/environment and results.
- KNOWN_ISSUES: incomplete work, limitations and manual checks.
- RELEASE_CHECKLIST: package, signing, permissions, privacy and artifact status.

Do not create empty reports that imply checks happened. If a check was not run, state `Not run` and explain why.
