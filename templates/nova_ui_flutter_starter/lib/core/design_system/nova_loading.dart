import 'package:flutter/material.dart';
import 'nova_motion.dart';
import 'nova_skeleton.dart';
import 'nova_spacing.dart';

/// A centered progress state for short operations.
class NovaLoadingIndicator extends StatelessWidget {
  const NovaLoadingIndicator({
    this.label,
    this.size = 24,
    super.key,
  });

  final String? label;
  final double size;

  @override
  Widget build(BuildContext context) {
    final indicator = SizedBox.square(
      dimension: size,
      child: const CircularProgressIndicator(strokeWidth: 2.5),
    );
    if (label == null) return Center(child: indicator);
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          indicator,
          const SizedBox(height: NovaSpacing.md),
          Text(label!, textAlign: TextAlign.center),
        ],
      ),
    );
  }
}

/// Full-area loading state; avoid artificial delays when data is ready.
class NovaFullScreenLoading extends StatelessWidget {
  const NovaFullScreenLoading({this.label = 'Loading…', super.key});
  final String label;

  @override
  Widget build(BuildContext context) => SafeArea(
        child: NovaLoadingIndicator(label: label, size: 30),
      );
}

/// Reusable skeleton row for list and profile loading placeholders.
class NovaSkeletonListTile extends StatelessWidget {
  const NovaSkeletonListTile({super.key});

  @override
  Widget build(BuildContext context) => const Padding(
        padding: EdgeInsets.symmetric(vertical: NovaSpacing.sm),
        child: Row(
          children: [
            NovaSkeleton(width: 48, height: 48, radius: NovaRadius.pill),
            SizedBox(width: NovaSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  NovaSkeleton(width: 150, height: 14),
                  SizedBox(height: 8),
                  NovaSkeleton(width: 220, height: 11),
                ],
              ),
            ),
          ],
        ),
      );
}

/// Button-like progress feedback with a label.
class NovaLoadingAction extends StatelessWidget {
  const NovaLoadingAction({
    required this.label,
    this.isLoading = false,
    this.onPressed,
    super.key,
  });

  final String label;
  final bool isLoading;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) => FilledButton(
        onPressed: isLoading ? null : onPressed,
        child: AnimatedSwitcher(
          duration: NovaMotion.fast,
          child: isLoading
              ? const SizedBox(
                  key: ValueKey('loading'),
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Colors.white,
                  ),
                )
              : Text(label, key: const ValueKey('label')),
        ),
      );
}

/// Empty state with a clear icon, message, and optional recovery action.
class NovaEmptyState extends StatelessWidget {
  const NovaEmptyState({
    required this.title,
    required this.message,
    this.icon = Icons.inbox_outlined,
    this.actionLabel,
    this.onAction,
    super.key,
  });

  final String title;
  final String message;
  final IconData icon;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(NovaSpacing.xxl),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon,
                  size: 48, color: Theme.of(context).colorScheme.primary),
              const SizedBox(height: NovaSpacing.lg),
              Text(title,
                  style: Theme.of(context).textTheme.titleLarge,
                  textAlign: TextAlign.center),
              const SizedBox(height: NovaSpacing.sm),
              Text(message, textAlign: TextAlign.center),
              if (actionLabel != null && onAction != null) ...[
                const SizedBox(height: NovaSpacing.lg),
                OutlinedButton(onPressed: onAction, child: Text(actionLabel!)),
              ],
            ],
          ),
        ),
      );
}

/// Compact offline/error state. Caller decides retry behavior.
class NovaErrorState extends StatelessWidget {
  const NovaErrorState({
    required this.title,
    required this.message,
    this.onRetry,
    super.key,
  });

  final String title;
  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => NovaEmptyState(
        title: title,
        message: message,
        icon: Icons.cloud_off_outlined,
        actionLabel: onRetry == null ? null : 'Try again',
        onAction: onRetry,
      );
}
