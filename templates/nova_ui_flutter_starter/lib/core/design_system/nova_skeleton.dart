import 'package:flutter/material.dart';
import 'nova_spacing.dart';

class NovaSkeleton extends StatefulWidget {
  const NovaSkeleton({
    this.width,
    this.height = 14,
    this.radius = NovaRadius.md,
    super.key,
  });

  final double? width;
  final double height;
  final double radius;

  @override
  State<NovaSkeleton> createState() => _NovaSkeletonState();
}

class _NovaSkeletonState extends State<NovaSkeleton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1100),
  )..repeat(reverse: true);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final base = Theme.of(context).brightness == Brightness.dark
        ? const Color(0xFF25334A)
        : const Color(0xFFE7ECF3);
    final highlight = Theme.of(context).brightness == Brightness.dark
        ? const Color(0xFF34445E)
        : const Color(0xFFF4F6FA);

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) => Container(
        width: widget.width,
        height: widget.height,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(widget.radius),
          color: Color.lerp(base, highlight, _controller.value),
        ),
      ),
    );
  }
}
