import 'package:flutter/material.dart';

enum NovaButtonVariant { primary, secondary, outline, text }

/// Standard button wrapper with a consistent 48px minimum touch target.
class NovaButton extends StatelessWidget {
  const NovaButton({
    required this.label,
    required this.onPressed,
    this.variant = NovaButtonVariant.primary,
    this.icon,
    this.isLoading = false,
    this.expand = false,
    super.key,
  });

  final String label;
  final VoidCallback? onPressed;
  final NovaButtonVariant variant;
  final IconData? icon;
  final bool isLoading;
  final bool expand;

  @override
  Widget build(BuildContext context) {
    final child = Row(
      mainAxisSize: expand ? MainAxisSize.max : MainAxisSize.min,
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (isLoading)
          const SizedBox.square(
            dimension: 18,
            child: CircularProgressIndicator(strokeWidth: 2),
          )
        else if (icon != null)
          Icon(icon, size: 18),
        if (isLoading || icon != null) const SizedBox(width: 8),
        Text(label),
      ],
    );

    final Widget button = switch (variant) {
      NovaButtonVariant.primary =>
        FilledButton(onPressed: isLoading ? null : onPressed, child: child),
      NovaButtonVariant.secondary => FilledButton.tonal(
          onPressed: isLoading ? null : onPressed, child: child),
      NovaButtonVariant.outline =>
        OutlinedButton(onPressed: isLoading ? null : onPressed, child: child),
      NovaButtonVariant.text =>
        TextButton(onPressed: isLoading ? null : onPressed, child: child),
    };

    return expand ? SizedBox(width: double.infinity, child: button) : button;
  }
}
