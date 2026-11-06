import 'package:flutter/material.dart';
import 'core/design_system/nova_theme.dart';
import 'features/showcase/nova_showcase_screen.dart';

void main() {
  runApp(const NovaUiApp());
}

class NovaUiApp extends StatefulWidget {
  const NovaUiApp({super.key});

  @override
  State<NovaUiApp> createState() => _NovaUiAppState();
}

class _NovaUiAppState extends State<NovaUiApp> {
  ThemeMode _themeMode = ThemeMode.system;

  void _toggleTheme(bool isDark) {
    setState(() => _themeMode = isDark ? ThemeMode.dark : ThemeMode.light);
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Nova UI',
      debugShowCheckedModeBanner: false,
      theme: NovaTheme.light(),
      darkTheme: NovaTheme.dark(),
      themeMode: _themeMode,
      home: NovaShowcaseScreen(
        onThemeChanged: _toggleTheme,
        isDark: _themeMode == ThemeMode.dark,
      ),
    );
  }
}
