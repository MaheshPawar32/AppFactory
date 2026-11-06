import 'package:flutter/material.dart';

/// Use on icon-only controls so screen readers can identify their purpose.
class NovaSemanticIconButton extends StatelessWidget {
  const NovaSemanticIconButton({
    required this.label,
    required this.icon,
    required this.onPressed,
    this.tooltip,
    super.key,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onPressed;
  final String? tooltip;

  @override
  Widget build(BuildContext context) => IconButton(
        tooltip: tooltip ?? label,
        onPressed: onPressed,
        icon: Icon(icon, semanticLabel: label),
        iconSize: 24,
        constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
      );
}
