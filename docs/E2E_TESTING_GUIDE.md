# End-to-end testing guide

Use Flutter integration tests for high-value user journeys that cross multiple screens or platform boundaries.

## Good candidates
- First launch and onboarding.
- Main create/edit/delete workflow.
- Form validation and submission failure.
- Local persistence across app restart where feasible.
- Search, filter and navigation flows.
- Permission denied and retry flows.
- Authentication expiry/sign-out if authentication exists.

## Rules
- Use deterministic test data and test backends or fakes where possible.
- Do not use real production credentials or production ad IDs in tests.
- Keep fast unit/widget tests separate from slower integration tests.
- Capture logs and screenshots when a test fails.
- Avoid flaky fixed-duration sleeps; wait for explicit state or finder conditions.
- Run tests on the configured emulator/device and report exact results.

## Typical command
```bash
flutter test integration_test
```
This command requires the project's integration tests and a configured device/emulator. It is not expected to pass if those are not present.
