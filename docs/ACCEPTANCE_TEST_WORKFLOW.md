# Acceptance Tests & Verification Workflow

1. Define acceptance criteria before implementation using `templates/project_docs/ACCEPTANCE_CRITERIA.md`.
2. Map each criterion to the smallest useful test:
   - Pure logic/data transformations → unit test.
   - UI state, validation, navigation and semantics → widget test.
   - Critical end-to-end journeys, persistence and platform integration → integration test or a documented manual test.
3. Track each result as `NOT RUN`, `PASS`, `FAIL` or `BLOCKED`. A test that was not executed is never a pass.
4. Capture exact commands, device/OS, date, logs and screenshots for failures and release candidates.
5. Run format, analyze and tests in a Flutter-installed environment. Review failures instead of suppressing or deleting tests to obtain a green run.
6. Keep external-service tests isolated; use test configuration and avoid real user data or production credentials.
7. Before release, complete the app-specific Definition of Done and create a Release Verification Record.

A test plan is not test evidence. Static audits do not prove runtime behavior, security, Play policy compliance or release readiness.
