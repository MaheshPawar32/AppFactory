# HTTP API client

Centralize request timeouts, JSON parsing, typed failures and safe retry policy.

## Dependency policy

This recipe does not add dependencies automatically. Review the target app's existing `pubspec.yaml`, SDK constraints, state management, and architecture first. Add only the selected package(s), pin compatible versions through normal Pub resolution, and record the decision in `DEPENDENCY_REVIEW.md`.

## Available choices

- `http`
- `dio`

## Acceptance checks

- [ ] Use the existing HTTP client if one already exists; otherwise choose one and document why.
- [ ] Set connection/receive timeouts and map errors to user-safe messages.
- [ ] Retry only safe/idempotent requests by default; never blindly retry writes.
- [ ] Keep secrets out of the app bundle and logs; test timeout, offline, non-2xx and malformed JSON.
