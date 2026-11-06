import 'package:flutter/material.dart';

/// Shared breakpoints for responsive page composition.
abstract final class NovaBreakpoints {
  static const double compact = 600;
  static const double medium = 840;
  static const double expanded = 1200;
}

enum NovaWindowSize { compact, medium, expanded }

NovaWindowSize novaWindowSizeOf(BuildContext context) {
  final width = MediaQuery.sizeOf(context).width;
  if (width < NovaBreakpoints.compact) return NovaWindowSize.compact;
  if (width < NovaBreakpoints.expanded) return NovaWindowSize.medium;
  return NovaWindowSize.expanded;
}

/// Constrains content width on tablets and desktop-sized windows.
class NovaContentFrame extends StatelessWidget {
  const NovaContentFrame({
    required this.child,
    this.maxWidth = 720,
    this.padding = const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
    super.key,
  });

  final Widget child;
  final double maxWidth;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) => Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: maxWidth),
          child: Padding(padding: padding, child: child),
        ),
      );
}
