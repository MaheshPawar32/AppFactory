import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nova_ui/main.dart';

void main() {
  testWidgets('Nova UI showcase renders core sections', (tester) async {
    await tester.pumpWidget(const NovaUiApp());
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Nova UI'), findsOneWidget);
    expect(find.text('Color tokens'), findsOneWidget);

    final buttonsHeading = find.text('Buttons');

    await tester.scrollUntilVisible(
      buttonsHeading,
      300,
      scrollable: find.byType(Scrollable).first,
    );

    expect(buttonsHeading, findsOneWidget);
  });
}
