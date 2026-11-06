# First-run onboarding

Explain the app value in a short, skippable first-run flow.

## Dependency policy

This recipe does not add dependencies automatically. Review the target app's existing `pubspec.yaml`, SDK constraints, state management, and architecture first. Add only the selected package(s), pin compatible versions through normal Pub resolution, and record the decision in `DEPENDENCY_REVIEW.md`.

## Available choices

- `three_page_intro`
- `permissions_education`
- `quick_setup`

## Acceptance checks

- [ ] Allow skip/back and never trap users in onboarding.
- [ ] Persist completion only after a valid finish or explicit skip.
- [ ] Do not request sensitive permissions before explaining their value.
- [ ] Add widget tests for first launch, completed launch, skip, and back navigation.
