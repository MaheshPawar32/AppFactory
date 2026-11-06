# Optional Firebase integration

Scaffold only the explicitly selected Firebase services.

## Dependency policy

This recipe does not add dependencies automatically. Review the target app's existing `pubspec.yaml`, SDK constraints, state management, and architecture first. Add only the selected package(s), pin compatible versions through normal Pub resolution, and record the decision in `DEPENDENCY_REVIEW.md`.

## Available choices

- `auth`
- `firestore`
- `crashlytics`
- `analytics`

## Acceptance checks

- [ ] Confirm platform targets and services before adding dependencies.
- [ ] Never invent google-services.json, GoogleService-Info.plist, API keys or project IDs.
- [ ] Use least-privilege security rules and exclude PII/secrets from telemetry.
- [ ] Mark each service NOT CONFIGURED until real project setup and runtime tests are evidenced.
