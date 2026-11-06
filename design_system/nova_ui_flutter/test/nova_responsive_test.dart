import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nova_ui/core/design_system/nova_responsive.dart';

void main() {
  testWidgets('uses compact breakpoint on a phone-sized surface',
      (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1;

    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) => const _BreakpointProbe(),
        ),
      ),
    );

    expect(find.text('compact'), findsOneWidget);

    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
}

class _BreakpointProbe extends StatelessWidget {
  const _BreakpointProbe();

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Center(child: Text(novaWindowSizeOf(context).name)),
      );
}
