# Nova UI — Flutter Design System

Nova UI is a reusable, Material 3-based Flutter design system starter with a live component showcase.

## Included

- Central semantic colors and theme tokens
- Light and dark theme support
- Typography, spacing, radius, and sizing tokens
- Reusable `NovaButton`, `NovaCard`, `NovaStatusBanner`, and `NovaSkeleton`
- Motion tokens, fade/slide transitions, press feedback, animated numbers, and page route helper
- Full-screen/inline loading, loading action, skeleton list tile, empty state, and retryable error state
- Interactive showcase for fields, chips, switches, checkboxes, sliders, dialogs, bottom sheets, and navigation
- A basic widget test
- No external runtime packages required

## Requirements

- Flutter 3.19+ (a recent stable Flutter SDK is recommended)
- Dart 3.3+

## Run

```bash
flutter pub get
flutter run
```

## Validate

```bash
dart format lib test
flutter analyze
flutter test
```

## Structure

```text
lib/
  main.dart
  core/
    design_system/
      nova_button.dart
      nova_card.dart
      nova_colors.dart
      nova_skeleton.dart
      nova_motion.dart
      nova_loading.dart
      nova_spacing.dart
      nova_status_banner.dart
      nova_theme.dart
      nova_typography.dart
  features/
    showcase/
      nova_showcase_screen.dart
test/
  widget_test.dart
```

## Use in another app

Copy `lib/core/design_system/` into your app, then import the desired component:

```dart
import 'core/design_system/nova_button.dart';

NovaButton(
  label: 'Continue',
  onPressed: () {},
)
```

Set your app themes:

```dart
MaterialApp(
  theme: NovaTheme.light(),
  darkTheme: NovaTheme.dark(),
  themeMode: ThemeMode.system,
)
```

Change tokens in `nova_colors.dart`, `nova_spacing.dart`, and `nova_typography.dart` instead of styling each screen independently.

## Customization

- Replace the primary brand colors in `NovaColors`.
- Adjust typography and scale in `NovaTypography`.
- Change spacing and corner radius values in `NovaSpacing` and `NovaRadius`.
- Add new reusable components in `lib/core/design_system/`.
- Keep app-specific business logic inside `lib/features/`.

## Notes

This is a starter design system, not a completed product app. Review the code against the Flutter SDK installed on your machine and run the validation commands before using it in production. The showcase navigation destinations are illustrative; the component demos are interactive.

No Firebase or AdMob dependencies are included by default. Add them only when an app requires them.
