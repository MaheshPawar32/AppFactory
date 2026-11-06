# Nova UI v1.2 — Added capabilities

## Shared components
- `NovaFormField`: labelled form input with helper/error text, validation, autofill and common input options.
- `NovaFeedback`: consistent success/info/warning/error SnackBar feedback.
- `NovaResponsive`: shared window breakpoints and a constrained content frame.
- `NovaSemanticIconButton`: accessible icon-only action with label and a minimum 48×48 touch target.
- `NovaBrandTheme`: create app-specific light/dark themes from a brand seed color.
- Existing motion/loading components remain available in `nova_motion.dart` and `nova_loading.dart`.

## Recommended use
1. Import only the components a feature needs; do not add a second component for the same purpose.
2. Use `Form` + `GlobalKey<FormState>` and validators for input validation. Do not rely only on button disabling.
3. Show loading, empty, error, success and offline states where the user journey needs them.
4. Use `NovaContentFrame` for long forms and reading pages; use responsive navigation patterns for larger windows.
5. Use semantic labels for icon-only actions and test with TalkBack and large text settings.
6. App-specific branding belongs in tokens/theme configuration, not hard-coded colors inside feature screens.

## Localization and offline UX
- Keep user-facing copy in ARB files (`lib/l10n/app_en.arb`, etc.) and generate localization code with Flutter's `gen-l10n`.
- Never concatenate translated sentences from fragments; use complete localized messages and plural/select messages.
- Offline-first apps should distinguish cached content from failed requests, preserve user-entered form data, provide retry actions, and avoid showing a success state before persistence succeeds.
- Keep permission explanations contextual and provide a graceful path when a permission is denied.

## QA and release gates
Run on a machine with Flutter installed:
```bash
flutter pub get
dart format --set-exit-if-changed .
flutter analyze
flutter test
flutter test --update-goldens # only when intentionally updating approved golden baselines
flutter build apk --debug
```
Add widget tests for validation, disabled/loading buttons, semantic labels, responsive breakpoints and error/empty states. Golden tests need reviewed baseline images and should not be updated blindly.

## Versioning and safe changes
- Keep reusable UI changes in `design_system/nova_ui_flutter/` first.
- Copy the approved changes into `templates/nova_ui_flutter_starter/` when updating the starter.
- Record breaking API changes in `CHANGELOG.md`; avoid changing component defaults silently.
- Claude must inspect existing files before editing, preserve app-specific business logic, and summarize files changed plus commands actually run.
