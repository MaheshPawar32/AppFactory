import 'package:flutter/material.dart';

/// Central motion tokens. Prefer these durations over ad-hoc timings.
abstract final class NovaMotion {
  static const Duration instant = Duration(milliseconds: 100);
  static const Duration fast = Duration(milliseconds: 150);
  static const Duration standard = Duration(milliseconds: 220);
  static const Duration medium = Duration(milliseconds: 280);
  static const Duration page = Duration(milliseconds: 320);
  static const Duration feedback = Duration(milliseconds: 360);
  static const Duration shimmer = Duration(milliseconds: 1200);

  static const Curve enter = Curves.easeOutCubic;
  static const Curve exit = Curves.easeInCubic;
  static const Curve standardCurve = Curves.easeInOutCubic;
}

/// Fade + vertical slide for content entering a screen.
class NovaFadeSlide extends StatelessWidget {
  const NovaFadeSlide({
    required this.child,
    this.duration = NovaMotion.medium,
    this.offset = 0.035,
    this.delay = Duration.zero,
    super.key,
  });

  final Widget child;
  final Duration duration;
  final double offset;
  final Duration delay;

  @override
  Widget build(BuildContext context) {
    final reduceMotion = MediaQuery.of(context).disableAnimations;
    if (reduceMotion) return child;
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: duration + delay,
      curve: NovaMotion.enter,
      builder: (context, value, child) {
        final adjusted = delay == Duration.zero
            ? value
            : ((value * (duration + delay).inMilliseconds -
                        delay.inMilliseconds) /
                    duration.inMilliseconds)
                .clamp(0.0, 1.0);
        return Opacity(
          opacity: adjusted,
          child: Transform.translate(
            offset: Offset(0, offset * 100 * (1 - adjusted)),
            child: child,
          ),
        );
      },
      child: child,
    );
  }
}

/// Reusable tap surface with restrained scale feedback.
class NovaPressable extends StatefulWidget {
  const NovaPressable({
    required this.child,
    required this.onPressed,
    this.borderRadius = const BorderRadius.all(Radius.circular(16)),
    super.key,
  });

  final Widget child;
  final VoidCallback? onPressed;
  final BorderRadius borderRadius;

  @override
  State<NovaPressable> createState() => _NovaPressableState();
}

class _NovaPressableState extends State<NovaPressable> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    final reduceMotion = MediaQuery.of(context).disableAnimations;
    return GestureDetector(
      onTap: widget.onPressed,
      onTapDown: widget.onPressed == null || reduceMotion
          ? null
          : (_) => setState(() => _pressed = true),
      onTapUp: (_) => setState(() => _pressed = false),
      onTapCancel: () => setState(() => _pressed = false),
      child: AnimatedScale(
        scale: _pressed ? 0.985 : 1,
        duration: NovaMotion.instant,
        curve: NovaMotion.standardCurve,
        child: ClipRRect(
          borderRadius: widget.borderRadius,
          child: widget.child,
        ),
      ),
    );
  }
}

/// Animated numeric value for dashboard metrics.
class NovaAnimatedNumber extends StatelessWidget {
  const NovaAnimatedNumber({
    required this.value,
    this.decimals = 0,
    this.prefix = '',
    this.suffix = '',
    this.style,
    super.key,
  });

  final double value;
  final int decimals;
  final String prefix;
  final String suffix;
  final TextStyle? style;

  @override
  Widget build(BuildContext context) {
    if (MediaQuery.of(context).disableAnimations) {
      return Text('$prefix${value.toStringAsFixed(decimals)}$suffix',
          style: style);
    }
    return TweenAnimationBuilder<double>(
      tween: Tween<double>(end: value),
      duration: NovaMotion.feedback,
      curve: NovaMotion.enter,
      builder: (context, current, _) => Text(
        '$prefix${current.toStringAsFixed(decimals)}$suffix',
        style: style,
      ),
    );
  }
}

/// Fade transition route helper for apps that use Navigator routes.
class NovaPageRoute<T> extends PageRouteBuilder<T> {
  NovaPageRoute({required Widget page})
      : super(
          transitionDuration: NovaMotion.page,
          reverseTransitionDuration: NovaMotion.fast,
          pageBuilder: (context, animation, secondaryAnimation) => page,
          transitionsBuilder: (context, animation, secondaryAnimation, child) {
            final reduceMotion = MediaQuery.of(context).disableAnimations;
            if (reduceMotion) return child;
            final curved = CurvedAnimation(
              parent: animation,
              curve: NovaMotion.enter,
              reverseCurve: NovaMotion.exit,
            );
            return FadeTransition(
              opacity: curved,
              child: SlideTransition(
                position: Tween<Offset>(
                  begin: const Offset(0, 0.025),
                  end: Offset.zero,
                ).animate(curved),
                child: child,
              ),
            );
          },
        );
}
