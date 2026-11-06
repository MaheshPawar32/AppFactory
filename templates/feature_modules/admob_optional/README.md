# Optional AdMob monetization

Add ads only when monetization is explicitly selected and consent requirements are addressed.

## Dependency policy

This recipe does not add dependencies automatically. Review the target app's existing `pubspec.yaml`, SDK constraints, state management, and architecture first. Add only the selected package(s), pin compatible versions through normal Pub resolution, and record the decision in `DEPENDENCY_REVIEW.md`.

## Available choices

- `banner`
- `interstitial`
- `rewarded`

## Acceptance checks

- [ ] Use Google test ad units during development; do not hardcode production IDs into shared templates.
- [ ] Place ads without obstructing core actions or accidental clicks.
- [ ] Implement applicable consent/privacy flows and age/audience requirements.
- [ ] Test load failure, no-fill, offline behavior, lifecycle and ad-free core usability.
