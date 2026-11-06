import 'package:flutter/material.dart';

enum NovaFeedbackType { success, info, warning, error }

/// App-wide lightweight feedback helpers. Keep messages short and actionable.
abstract final class NovaFeedback {
  static void show(
    BuildContext context, {
    required String message,
    NovaFeedbackType type = NovaFeedbackType.info,
    String? actionLabel,
    VoidCallback? onAction,
  }) {
    final messenger = ScaffoldMessenger.of(context);
    messenger
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          behavior: SnackBarBehavior.floating,
          content: Row(
            children: [
              Icon(_icon(type), size: 20, color: Colors.white),
              const SizedBox(width: 12),
              Expanded(child: Text(message)),
            ],
          ),
          action: actionLabel == null
              ? null
              : SnackBarAction(
                  label: actionLabel, onPressed: onAction ?? () {}),
        ),
      );
  }

  static IconData _icon(NovaFeedbackType type) => switch (type) {
        NovaFeedbackType.success => Icons.check_circle_outline,
        NovaFeedbackType.info => Icons.info_outline,
        NovaFeedbackType.warning => Icons.warning_amber_rounded,
        NovaFeedbackType.error => Icons.error_outline,
      };
}
