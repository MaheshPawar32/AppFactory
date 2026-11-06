import 'package:flutter/material.dart';
import 'nova_colors.dart';
import 'nova_spacing.dart';

enum NovaStatus { success, warning, error, info }

class NovaStatusBanner extends StatelessWidget {
  const NovaStatusBanner({
    required this.title,
    required this.message,
    required this.status,
    super.key,
  });

  final String title;
  final String message;
  final NovaStatus status;

  @override
  Widget build(BuildContext context) {
    final (color, icon) = switch (status) {
      NovaStatus.success => (NovaColors.success, Icons.check_circle_outline),
      NovaStatus.warning => (NovaColors.warning, Icons.warning_amber_rounded),
      NovaStatus.error => (NovaColors.error, Icons.error_outline),
      NovaStatus.info => (NovaColors.info, Icons.info_outline),
    };
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(NovaSpacing.md),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(NovaRadius.md),
        border: Border.all(color: color.withValues(alpha: 0.25)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color),
          const SizedBox(width: NovaSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: Theme.of(context)
                        .textTheme
                        .titleSmall
                        ?.copyWith(color: color)),
                const SizedBox(height: NovaSpacing.xs),
                Text(message),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
