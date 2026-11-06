# Localization starter: English, Hindi and Marathi

1. Enable Flutter localization generation in `pubspec.yaml`:
```yaml
flutter:
  generate: true
```
2. Add `flutter_localizations` from the Flutter SDK and `intl` if required by your Flutter localization setup.
3. Create `lib/l10n/app_en.arb`, `app_hi.arb`, and `app_mr.arb`.
4. Use generated localization delegates and supported locales in `MaterialApp`.
5. Keep complete messages in ARB files; use plural/select patterns for dynamic text.
6. Check text expansion, date/number formats, accessibility labels and font rendering.
7. Provide a language selector only if the product needs in-app language choice.

Do not automatically translate legal, financial, safety or medical copy without review. The factory does not ship complete translations for any app; each app must provide and review its own copy.
