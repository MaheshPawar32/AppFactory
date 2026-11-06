import 'package:flutter/material.dart';

/// Nova UI Signature palette. Use semantic tokens rather than raw colors.
abstract final class NovaColors {
  static const primary = Color(0xFF7566E8);
  static const primaryLight = Color(0xFFC5B7FF);
  static const primaryDark = Color(0xFF5949C8);
  static const secondary = Color(0xFFC6A978);
  static const success = Color(0xFF2D9B78);
  static const warning = Color(0xFFD69A45);
  static const error = Color(0xFFD76570);
  static const info = Color(0xFF6689C9);

  static const lightBackground = Color(0xFFF8F7F4);
  static const lightSurface = Color(0xFFFFFFFF);
  static const lightText = Color(0xFF242331);
  static const lightMutedText = Color(0xFF777584);
  static const lightBorder = Color(0xFFEAE8E3);

  static const darkBackground = Color(0xFF101014);
  static const darkSurface = Color(0xFF1B1A22);
  static const darkElevated = Color(0xFF24222D);
  static const darkText = Color(0xFFEAE7F2);
  static const darkMutedText = Color(0xFFA39EAF);
  static const darkBorder = Color(0xFF34313F);

  static const gradientPrimary = LinearGradient(
    colors: [Color(0xFF5949C8), Color(0xFF9B8CF5), Color(0xFFC5B7FF)],
    begin: Alignment.bottomLeft,
    end: Alignment.topRight,
  );
  static const gradientSignature = LinearGradient(
    colors: [Color(0xFF242039), Color(0xFF5949C8), Color(0xFF8C7DEB)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
}
