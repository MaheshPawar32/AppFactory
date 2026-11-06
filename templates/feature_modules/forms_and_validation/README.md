# Forms and validation

Build accessible forms with inline validation, safe submission state and keyboard handling.

## Dependency policy

This recipe does not add dependencies automatically. Review the target app's existing `pubspec.yaml`, SDK constraints, state management, and architecture first. Add only the selected package(s), pin compatible versions through normal Pub resolution, and record the decision in `DEPENDENCY_REVIEW.md`.

## Available choices

- `simple_form`
- `multi_step_form`
- `search_and_filter`

## Acceptance checks

- [ ] Use the existing state-management choice; do not introduce a second state-management framework.
- [ ] Validate on submit and then provide helpful inline feedback.
- [ ] Prevent duplicate submissions and preserve safe input when recoverable errors occur.
- [ ] Test invalid, valid, keyboard, loading, server-error, and accessibility cases.
