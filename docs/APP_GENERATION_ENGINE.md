# App Generation Engine

Use this before implementation so Claude creates a complete plan instead of jumping straight into code.

## Stage 1 — Discovery
Capture:
- New or existing app; app name and purpose.
- Target users and their main problem.
- Android package name and display name.
- Offline/local data, remote APIs, authentication and synchronization needs.
- Firebase services, AdMob formats, notifications, analytics and crash reporting choices.
- Languages, accessibility expectations and supplied UI reference images.
- Monetization and privacy/data deletion requirements.

Do not block on optional details. Record assumptions explicitly and ask only questions that materially affect architecture, cost, privacy or app behavior.

## Stage 2 — Planning artifacts
Before coding, produce:
1. One-paragraph product summary and MVP scope.
2. Screen inventory with purpose and primary actions.
3. Navigation map and back-navigation behavior.
4. Data model and persistence plan.
5. Feature/module selection list with reasons.
6. Loading, empty, error, offline, permission-denied and success states per relevant screen.
7. UI reference-to-screen mapping.
8. Dependencies and compatibility notes.
9. Test plan and release checklist.
10. Risks, assumptions and unresolved decisions.

## Stage 3 — Design
- Use Nova UI tokens and shared components.
- Apply app-specific brand colors without hard-coding colors into feature widgets.
- Use real Flutter widgets, not screenshots as screens.
- Build all key screen states, not only the happy path.
- Respect keyboard behavior, large text, screen readers, reduced motion and Android back navigation.
- For visual references, compare spacing, hierarchy, typography, component shape, color, and responsive behavior. Report differences rather than claiming pixel-perfect matching without visual verification.

## Stage 4 — Implementation
- Implement in feature-sized increments.
- Use the existing state-management approach for an existing app. Provider is the default for a new app unless the user chooses otherwise.
- Add packages only when needed and explain the trade-off.
- Keep persistence, API access and business logic outside presentation widgets where practical.
- Do not implement fake actions or placeholder success messages for unimplemented features.

## Stage 5 — Verification
- Run format, analyze, unit/widget tests and debug build when Flutter is available.
- Add tests for critical flows and form validation.
- Check empty/error/offline states and at least one small Android viewport.
- Label each check as passed, failed, or not run based on actual command output.
- Keep a list of remaining manual checks.

The `scripts/create_app.py` workflow excludes Flutter build/cache folders, IDE
files, local Android SDK/signing configuration, and local `.env` files. It
preserves `.env.example`, generates Android platform files with the installed
Flutter SDK in an isolated temporary workspace, wires the Android package
identity, and adds development/staging/production flavors. Review
`APP_FACTORY_METADATA.md`, `APP_CONFIG.json`, and `STORE_ASSET_INVENTORY.json`.
Generated flavors require a matching `--flavor` and
`--dart-define=APP_ENV=<environment>` when building. API URLs may be supplied
through Dart defines; never pass server secrets into a client build.

The Flutter build engine supports optional `--flavor` and repeatable
`--dart-define KEY=VALUE` arguments for its artifact build step. Its analysis
and test steps remain ordinary project checks. Use `--dry-run` to inspect the
planned command first. It does not configure release signing or publish.
