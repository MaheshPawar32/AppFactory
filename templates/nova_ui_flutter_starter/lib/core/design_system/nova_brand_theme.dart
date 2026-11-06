import 'package:flutter/material.dart';

/// Creates app-specific color schemes without changing shared component APIs.
/// Choose a brand seed per app; keep contrast and semantic colors accessible.
abstract final class NovaBrandTheme {
  static ThemeData light(Color seedColor) =>
      _build(seedColor, Brightness.light);
  static ThemeData dark(Color seedColor) => _build(seedColor, Brightness.dark);

  static ThemeData _build(Color seedColor, Brightness brightness) {
    final scheme = ColorScheme.fromSeed(
      seedColor: seedColor,
      brightness: brightness,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      brightness: brightness,
      visualDensity: VisualDensity.standard,
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(48, 48),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
      ),
    );
  }
}
