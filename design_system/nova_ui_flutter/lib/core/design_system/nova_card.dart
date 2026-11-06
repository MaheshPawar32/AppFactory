import 'package:flutter/material.dart';
import 'nova_spacing.dart';

class NovaCard extends StatelessWidget {
  const NovaCard({
    required this.child,
    this.padding = const EdgeInsets.all(NovaSpacing.lg),
    this.onTap,
    this.header,
    super.key,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;
  final Widget? header;

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: padding,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (header != null) ...[
                header!,
                const SizedBox(height: NovaSpacing.md)
              ],
              child,
            ],
          ),
        ),
      ),
    );
  }
}
