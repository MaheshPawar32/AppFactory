# Nova UI Signature Edition 3.0

This update refines the visual foundation while preserving the existing component APIs and showcase sections.

## Visual direction
- Royal Iris primary: `#7566E8`
- Lavender highlight: `#C5B7FF`
- Champagne accent: `#C6A978`
- Warm porcelain light surfaces and deep ink dark surfaces
- Refined typography rhythm, softer borders, and quieter elevation
- Signature gradient hero on the component showcase
- Consistent Material 3 treatments for cards, forms, buttons, chips, dialogs, sheets, sliders, and feedback

## Verify on your Mac
```bash
flutter clean
flutter pub get
dart format lib test
flutter analyze
flutter test
flutter build apk --debug
```

If analyzer reports an SDK-specific API issue, share the full output and I can patch it.
