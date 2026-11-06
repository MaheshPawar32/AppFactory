import 'package:flutter/material.dart';
import 'nova_colors.dart';
import 'nova_spacing.dart';
import 'nova_typography.dart';

abstract final class NovaTheme {
  static ThemeData light() => _build(Brightness.light);
  static ThemeData dark() => _build(Brightness.dark);

  static ThemeData _build(Brightness brightness) {
    final isDark = brightness == Brightness.dark;
    final background =
        isDark ? NovaColors.darkBackground : NovaColors.lightBackground;
    final surface = isDark ? NovaColors.darkSurface : NovaColors.lightSurface;
    final elevated = isDark ? NovaColors.darkElevated : const Color(0xFFF0EEF8);
    final text = isDark ? NovaColors.darkText : NovaColors.lightText;
    final muted = isDark ? NovaColors.darkMutedText : NovaColors.lightMutedText;
    final border = isDark ? NovaColors.darkBorder : NovaColors.lightBorder;
    final scheme = ColorScheme(
      brightness: brightness,
      primary: NovaColors.primary,
      onPrimary: Colors.white,
      secondary: NovaColors.secondary,
      onSecondary: const Color(0xFF282333),
      error: NovaColors.error,
      onError: Colors.white,
      surface: surface,
      onSurface: text,
      surfaceContainerHighest: elevated,
      onSurfaceVariant: muted,
      outline: border,
      outlineVariant: border,
      shadow: Colors.black.withValues(alpha: isDark ? .28 : .04),
      scrim: Colors.black54,
      inverseSurface:
          isDark ? const Color(0xFFF8F7F4) : const Color(0xFF242331),
      onInverseSurface: isDark ? const Color(0xFF242331) : Colors.white,
      inversePrimary: NovaColors.primaryLight,
      tertiary: NovaColors.secondary,
      onTertiary: const Color(0xFF242331),
    );

    final rounded = RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(NovaRadius.lg),
      side: BorderSide(color: border),
    );
    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: scheme,
      scaffoldBackgroundColor: background,
      canvasColor: background,
      fontFamily: NovaTypography.fontFamily,
      splashFactory: InkSparkle.splashFactory,
      visualDensity: VisualDensity.standard,
      textTheme: TextTheme(
        displayLarge: NovaTypography.display
            .copyWith(color: text, letterSpacing: -1.5, height: 1.08),
        headlineMedium: NovaTypography.headline
            .copyWith(color: text, letterSpacing: -.7, height: 1.15),
        titleLarge:
            NovaTypography.title.copyWith(color: text, letterSpacing: -.25),
        bodyLarge: NovaTypography.body.copyWith(color: text, height: 1.55),
        bodyMedium: NovaTypography.bodySmall.copyWith(color: text, height: 1.5),
        bodySmall: NovaTypography.caption.copyWith(color: muted, height: 1.45),
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: background,
        foregroundColor: text,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
            color: text,
            fontSize: 17,
            fontWeight: FontWeight.w700,
            letterSpacing: -.3),
      ),
      cardTheme: CardThemeData(
        color: surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        surfaceTintColor: Colors.transparent,
        shape: rounded,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: isDark ? elevated : const Color(0xFFFBFAF8),
        contentPadding: const EdgeInsets.symmetric(
            horizontal: NovaSpacing.lg, vertical: NovaSpacing.md),
        hintStyle: TextStyle(color: muted),
        labelStyle: TextStyle(color: muted),
        border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(NovaRadius.md),
            borderSide: BorderSide(color: border)),
        enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(NovaRadius.md),
            borderSide: BorderSide(color: border)),
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(NovaRadius.md),
            borderSide:
                const BorderSide(color: NovaColors.primary, width: 1.6)),
        errorBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(NovaRadius.md),
            borderSide: const BorderSide(color: NovaColors.error)),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          foregroundColor: Colors.white,
          backgroundColor: NovaColors.primaryDark,
          minimumSize: const Size(48, 48),
          padding: const EdgeInsets.symmetric(
              horizontal: NovaSpacing.xl, vertical: NovaSpacing.md),
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(NovaRadius.md)),
          textStyle:
              const TextStyle(fontWeight: FontWeight.w700, letterSpacing: -.1),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: text,
          minimumSize: const Size(48, 48),
          padding: const EdgeInsets.symmetric(
              horizontal: NovaSpacing.xl, vertical: NovaSpacing.md),
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(NovaRadius.md)),
          side: BorderSide(color: border),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
          style: TextButton.styleFrom(foregroundColor: NovaColors.primary)),
      chipTheme: ChipThemeData(
        backgroundColor: elevated,
        selectedColor: NovaColors.primary.withValues(alpha: .14),
        labelStyle: TextStyle(color: text, fontWeight: FontWeight.w600),
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(NovaRadius.pill)),
        side: BorderSide(color: border),
        padding: const EdgeInsets.symmetric(
            horizontal: NovaSpacing.sm, vertical: NovaSpacing.xs),
      ),
      dividerTheme:
          DividerThemeData(color: border, thickness: 1, space: NovaSpacing.xl),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor:
            isDark ? NovaColors.darkElevated : const Color(0xFF282633),
        contentTextStyle:
            const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
        shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(NovaRadius.md)),
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((states) =>
            states.contains(WidgetState.selected) ? Colors.white : null),
        trackColor: WidgetStateProperty.resolveWith((states) =>
            states.contains(WidgetState.selected) ? NovaColors.primary : null),
      ),
      progressIndicatorTheme:
          const ProgressIndicatorThemeData(color: NovaColors.primary),
      sliderTheme: SliderThemeData(
          activeTrackColor: NovaColors.primary,
          thumbColor: NovaColors.primary,
          inactiveTrackColor: border),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
        shape: const RoundedRectangleBorder(
            borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
      ),
    );
  }
}
