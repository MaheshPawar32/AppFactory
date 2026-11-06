import 'package:flutter/material.dart';
import '../../core/design_system/nova_button.dart';
import '../../core/design_system/nova_card.dart';
import '../../core/design_system/nova_loading.dart';
import '../../core/design_system/nova_motion.dart';
import '../../core/design_system/nova_colors.dart';
import '../../core/design_system/nova_skeleton.dart';
import '../../core/design_system/nova_spacing.dart';
import '../../core/design_system/nova_status_banner.dart';

class NovaShowcaseScreen extends StatefulWidget {
  const NovaShowcaseScreen({
    required this.onThemeChanged,
    required this.isDark,
    super.key,
  });

  final ValueChanged<bool> onThemeChanged;
  final bool isDark;

  @override
  State<NovaShowcaseScreen> createState() => _NovaShowcaseScreenState();
}

class _NovaShowcaseScreenState extends State<NovaShowcaseScreen> {
  int _navigationIndex = 0;
  bool _switchValue = true;
  bool _checkboxValue = false;
  double _sliderValue = 0.5;
  String _selectedChip = 'All';
  final _textController = TextEditingController();

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                gradient: NovaColors.gradientPrimary,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.layers_rounded, color: Colors.white),
            ),
            const SizedBox(width: 10),
            const Flexible(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Nova UI',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontWeight: FontWeight.w800)),
                  Text('SIGNATURE DESIGN SYSTEM',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                          fontSize: 11, fontWeight: FontWeight.normal)),
                ],
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Toggle dark theme',
            onPressed: () => widget.onThemeChanged(!widget.isDark),
            icon: Icon(widget.isDark
                ? Icons.light_mode_outlined
                : Icons.dark_mode_outlined),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
              NovaSpacing.lg, NovaSpacing.md, NovaSpacing.lg, 100),
          children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                gradient: NovaColors.gradientSignature,
                borderRadius: BorderRadius.circular(28),
                boxShadow: [
                  BoxShadow(
                    color: NovaColors.primary.withValues(alpha: 0.18),
                    blurRadius: 28,
                    offset: const Offset(0, 14),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Flexible(
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 6),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: .14),
                            borderRadius: BorderRadius.circular(30),
                            border: Border.all(
                                color: Colors.white.withValues(alpha: .22)),
                          ),
                          child: const Text(
                            'SIGNATURE EDITION  ·  3.0',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                                color: Colors.white,
                                fontSize: 10,
                                fontWeight: FontWeight.w800,
                                letterSpacing: 1.1),
                          ),
                        ),
                      ),
                      const Spacer(),
                      const Icon(Icons.auto_awesome_rounded,
                          color: Color(0xFFC6A978), size: 22),
                    ],
                  ),
                  const SizedBox(height: 26),
                  const Text(
                    'Thoughtful design.\nBeautifully built.',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 29,
                        height: 1.12,
                        fontWeight: FontWeight.w800,
                        letterSpacing: -1.1),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'A refined Flutter foundation for products that feel effortless.',
                    style: TextStyle(
                        color: Colors.white.withValues(alpha: .78),
                        fontSize: 13,
                        height: 1.5),
                  ),
                  const SizedBox(height: 22),
                  Wrap(
                    spacing: 16,
                    runSpacing: 6,
                    children: [
                      for (final label in const [
                        'Design tokens',
                        'Light + dark'
                      ])
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.check_circle_rounded,
                                color: Color(0xFFC6A978), size: 16),
                            const SizedBox(width: 7),
                            Text(label,
                                style: TextStyle(
                                    color: Colors.white.withValues(alpha: .9),
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600)),
                          ],
                        ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: NovaSpacing.xl),
            Text('Build beautifully.', style: theme.textTheme.headlineMedium),
            const SizedBox(height: NovaSpacing.xs),
            Text(
              'A reusable Flutter UI foundation for consistent, accessible apps.',
              style: theme.textTheme.bodyMedium
                  ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
            ),
            const SizedBox(height: NovaSpacing.xl),
            _sectionHeader(context, '01', 'Color tokens'),
            const NovaCard(
              child: Wrap(
                spacing: NovaSpacing.md,
                runSpacing: NovaSpacing.md,
                children: [
                  _ColorToken(name: 'Primary', color: NovaColors.primary),
                  _ColorToken(name: 'Secondary', color: NovaColors.secondary),
                  _ColorToken(name: 'Success', color: NovaColors.success),
                  _ColorToken(name: 'Warning', color: NovaColors.warning),
                  _ColorToken(name: 'Error', color: NovaColors.error),
                  _ColorToken(name: 'Info', color: NovaColors.info),
                ],
              ),
            ),
            const SizedBox(height: NovaSpacing.xl),
            _sectionHeader(context, '02', 'Typography'),
            NovaCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Display / 32',
                      style: theme.textTheme.displaySmall
                          ?.copyWith(fontWeight: FontWeight.w800)),
                  const SizedBox(height: 8),
                  Text('Headline / 24', style: theme.textTheme.headlineMedium),
                  const SizedBox(height: 8),
                  Text('Section title / 18', style: theme.textTheme.titleLarge),
                  const SizedBox(height: 8),
                  const Text(
                      'Body text / 16 — readable, comfortable, and clear across screens.'),
                  const SizedBox(height: 6),
                  Text('Caption / 12 — secondary information and metadata.',
                      style: theme.textTheme.bodySmall),
                ],
              ),
            ),
            const SizedBox(height: NovaSpacing.xl),
            _sectionHeader(context, '03', 'Buttons'),
            NovaCard(
              child: Wrap(
                spacing: NovaSpacing.sm,
                runSpacing: NovaSpacing.sm,
                children: [
                  NovaButton(
                      label: 'Primary',
                      onPressed: () => _showMessage('Primary button tapped')),
                  NovaButton(
                      label: 'Secondary',
                      variant: NovaButtonVariant.secondary,
                      onPressed: () => _showMessage('Secondary tapped')),
                  NovaButton(
                      label: 'Outline',
                      variant: NovaButtonVariant.outline,
                      onPressed: () => _showMessage('Outline tapped')),
                  NovaButton(
                      label: 'Text',
                      variant: NovaButtonVariant.text,
                      onPressed: () => _showMessage('Text tapped')),
                  NovaButton(
                      label: 'With icon',
                      icon: Icons.add_rounded,
                      onPressed: () => _showMessage('Action created')),
                ],
              ),
            ),
            const SizedBox(height: NovaSpacing.xl),
            _sectionHeader(context, '04', 'Inputs'),
            NovaCard(
              child: Column(
                children: [
                  TextField(
                    controller: _textController,
                    decoration: const InputDecoration(
                      labelText: 'Your name',
                      hintText: 'Enter a name',
                      prefixIcon: Icon(Icons.person_outline),
                    ),
                  ),
                  const SizedBox(height: NovaSpacing.md),
                  NovaButton(
                    label: 'Show entered value',
                    expand: true,
                    onPressed: () => _showMessage(
                      _textController.text.trim().isEmpty
                          ? 'Please enter a value first'
                          : 'Hello, ${_textController.text.trim()}',
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: NovaSpacing.xl),
            _sectionHeader(context, '05', 'Cards and list items'),
            NovaCard(
              onTap: () => _showMessage('Card selected'),
              child: Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: NovaColors.primary.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(NovaRadius.md),
                    ),
                    child: const Icon(Icons.auto_awesome_rounded,
                        color: NovaColors.primary),
                  ),
                  const SizedBox(width: NovaSpacing.md),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Reusable content card',
                            style: TextStyle(fontWeight: FontWeight.w700)),
                        SizedBox(height: 4),
                        Text('Tap to see the interaction pattern.'),
                      ],
                    ),
                  ),
                  const Icon(Icons.chevron_right_rounded),
                ],
              ),
            ),
            const SizedBox(height: NovaSpacing.xl),
            _sectionHeader(context, '06', 'Chips and selection'),
            NovaCard(
              child: Wrap(
                spacing: NovaSpacing.sm,
                children: ['All', 'Popular', 'Recent', 'Saved'].map((label) {
                  return ChoiceChip(
                    label: Text(label),
                    selected: _selectedChip == label,
                    onSelected: (_) => setState(() => _selectedChip = label),
                  );
                }).toList(),
              ),
            ),
            const SizedBox(height: NovaSpacing.xl),
            _sectionHeader(context, '07', 'Controls'),
            NovaCard(
              child: Column(
                children: [
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Notifications'),
                    subtitle: const Text('Switches use the app theme'),
                    value: _switchValue,
                    onChanged: (value) => setState(() => _switchValue = value),
                  ),
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Remember preference'),
                    value: _checkboxValue,
                    onChanged: (value) =>
                        setState(() => _checkboxValue = value ?? false),
                  ),
                  Row(
                    children: [
                      const Text('Slider'),
                      Expanded(
                        child: Slider(
                          value: _sliderValue,
                          onChanged: (value) =>
                              setState(() => _sliderValue = value),
                        ),
                      ),
                      Text('${(_sliderValue * 100).round()}%'),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: NovaSpacing.xl),
            _sectionHeader(context, '08', 'Status and feedback'),
            const NovaStatusBanner(
              title: 'Success',
              message: 'Your changes have been saved.',
              status: NovaStatus.success,
            ),
            const SizedBox(height: NovaSpacing.sm),
            const NovaStatusBanner(
              title: 'Heads up',
              message: 'Review this information before continuing.',
              status: NovaStatus.warning,
            ),
            const SizedBox(height: NovaSpacing.sm),
            const NovaStatusBanner(
              title: 'Something went wrong',
              message: 'Show a clear recovery action whenever possible.',
              status: NovaStatus.error,
            ),
            const SizedBox(height: NovaSpacing.xl),
            _sectionHeader(context, '09', 'Loading skeletons'),
            const NovaCard(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  NovaSkeleton(width: 52, height: 52, radius: 26),
                  SizedBox(width: NovaSpacing.md),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        NovaSkeleton(width: 150, height: 16),
                        SizedBox(height: 10),
                        NovaSkeleton(width: double.infinity, height: 12),
                        SizedBox(height: 8),
                        NovaSkeleton(width: 210, height: 12),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: NovaSpacing.xl),
            _sectionHeader(context, '10', 'Dialogs and bottom sheets'),
            NovaCard(
              child: Wrap(
                spacing: NovaSpacing.sm,
                runSpacing: NovaSpacing.sm,
                children: [
                  OutlinedButton.icon(
                    onPressed: () async {
                      final result = await showDialog<bool>(
                        context: context,
                        builder: (dialogContext) => AlertDialog(
                          title: const Text('Confirm action?'),
                          content: const Text(
                              'This is a reusable confirmation dialog pattern.'),
                          actions: [
                            TextButton(
                                onPressed: () =>
                                    Navigator.pop(dialogContext, false),
                                child: const Text('Cancel')),
                            FilledButton(
                                onPressed: () =>
                                    Navigator.pop(dialogContext, true),
                                child: const Text('Confirm')),
                          ],
                        ),
                      );
                      if (result == true && mounted) _showMessage('Confirmed');
                    },
                    icon: const Icon(Icons.chat_bubble_outline),
                    label: const Text('Show dialog'),
                  ),
                  OutlinedButton.icon(
                    onPressed: () => showModalBottomSheet<void>(
                      context: context,
                      showDragHandle: true,
                      builder: (sheetContext) => SafeArea(
                        child: Padding(
                          padding: const EdgeInsets.all(NovaSpacing.xl),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Bottom sheet',
                                  style:
                                      Theme.of(context).textTheme.titleLarge),
                              const SizedBox(height: 8),
                              const Text(
                                  'Use sheets for focused actions and supporting content.'),
                              const SizedBox(height: NovaSpacing.xl),
                              NovaButton(
                                label: 'Close',
                                expand: true,
                                onPressed: () => Navigator.pop(sheetContext),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                    icon: const Icon(Icons.vertical_align_top_rounded),
                    label: const Text('Show sheet'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: NovaSpacing.xl),
            _sectionHeader(context, '11', 'Spacing and radius'),
            const NovaCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Spacing scale: 4, 8, 12, 16, 24, 32, 48'),
                  SizedBox(height: NovaSpacing.md),
                  Wrap(
                    crossAxisAlignment: WrapCrossAlignment.end,
                    spacing: NovaSpacing.sm,
                    children: [
                      _SpacingSwatch(size: 4),
                      _SpacingSwatch(size: 8),
                      _SpacingSwatch(size: 12),
                      _SpacingSwatch(size: 16),
                      _SpacingSwatch(size: 24),
                      _SpacingSwatch(size: 32),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: NovaSpacing.xl),
            _sectionHeader(context, '12', 'Accessibility baseline'),
            const NovaStatusBanner(
              title: 'Built-in principles',
              message:
                  'Use semantic labels, scalable text, adequate contrast, 48px minimum touch targets, and clear error messages.',
              status: NovaStatus.info,
            ),
            const SizedBox(height: NovaSpacing.xl),
            _sectionHeader(context, '13', 'Loading and empty states'),
            NovaCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const NovaLoadingIndicator(
                      label: 'Loading example', size: 24),
                  const SizedBox(height: NovaSpacing.xl),
                  const NovaSkeletonListTile(),
                  const NovaSkeletonListTile(),
                  const SizedBox(height: NovaSpacing.md),
                  NovaLoadingAction(
                    label: 'Simulate save',
                    isLoading: _switchValue,
                    onPressed: () => _showMessage('Action completed'),
                  ),
                  const SizedBox(height: NovaSpacing.md),
                  NovaButton(
                    label: 'Show empty state',
                    variant: NovaButtonVariant.outline,
                    onPressed: () => showDialog<void>(
                      context: context,
                      builder: (dialogContext) => AlertDialog(
                        content: const SizedBox(
                          width: 320,
                          height: 250,
                          child: NovaEmptyState(
                            title: 'Nothing here yet',
                            message:
                                'Your items will appear here when you add them.',
                            icon: Icons.inbox_outlined,
                          ),
                        ),
                        actions: [
                          TextButton(
                              onPressed: () => Navigator.pop(dialogContext),
                              child: const Text('Close')),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: NovaSpacing.xl),
            _sectionHeader(context, '14', 'Motion and micro-interactions'),
            NovaCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Standard motion: 220 ms • Page motion: 320 ms'),
                  const SizedBox(height: NovaSpacing.md),
                  NovaPressable(
                    onPressed: () =>
                        _showMessage('Press feedback demonstrated'),
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(NovaSpacing.xl),
                      decoration: BoxDecoration(
                        gradient: NovaColors.gradientPrimary,
                        borderRadius: BorderRadius.circular(NovaRadius.lg),
                      ),
                      child: const Row(
                        children: [
                          Icon(Icons.touch_app_rounded, color: Colors.white),
                          SizedBox(width: NovaSpacing.md),
                          Expanded(
                            child: Text(
                              'Tap this animated surface',
                              style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w700),
                            ),
                          ),
                          Icon(Icons.arrow_forward_rounded,
                              color: Colors.white),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: NovaSpacing.lg),
                  NovaAnimatedNumber(
                    value: 1284,
                    prefix: '',
                    suffix: ' users',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const SizedBox(height: NovaSpacing.md),
                  NovaButton(
                    label: 'Preview page transition',
                    icon: Icons.open_in_new_rounded,
                    onPressed: () => Navigator.of(context).push(
                      NovaPageRoute<void>(page: const _MotionPreviewPage()),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: NovaSpacing.xl),
            Center(
              child: Text(
                'Nova UI • Design system v1.1',
                style: theme.textTheme.bodySmall,
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _navigationIndex,
        onDestinationSelected: (index) {
          setState(() => _navigationIndex = index);
          if (index != 0) {
            _showMessage('${[
              'Home',
              'Components',
              'Tokens',
              'Settings'
            ][index]} is a showcase navigation example.');
          }
        },
        destinations: const [
          NavigationDestination(
              icon: Icon(Icons.home_outlined),
              selectedIcon: Icon(Icons.home_rounded),
              label: 'Home'),
          NavigationDestination(
              icon: Icon(Icons.widgets_outlined),
              selectedIcon: Icon(Icons.widgets_rounded),
              label: 'Components'),
          NavigationDestination(
              icon: Icon(Icons.palette_outlined),
              selectedIcon: Icon(Icons.palette_rounded),
              label: 'Tokens'),
          NavigationDestination(
              icon: Icon(Icons.settings_outlined),
              selectedIcon: Icon(Icons.settings_rounded),
              label: 'Settings'),
        ],
      ),
    );
  }

  Widget _sectionHeader(BuildContext context, String number, String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: NovaSpacing.md),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
            decoration: BoxDecoration(
              color: NovaColors.primary.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(NovaRadius.sm),
            ),
            child: Text(number,
                style: const TextStyle(
                    color: NovaColors.primary,
                    fontWeight: FontWeight.w700,
                    fontSize: 12)),
          ),
          const SizedBox(width: NovaSpacing.sm),
          Text(title, style: Theme.of(context).textTheme.titleLarge),
        ],
      ),
    );
  }
}

class _ColorToken extends StatelessWidget {
  const _ColorToken({required this.name, required this.color});
  final String name;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 76,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            height: 42,
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(NovaRadius.md),
            ),
          ),
          const SizedBox(height: 6),
          Text(name, style: Theme.of(context).textTheme.labelMedium),
          Text(
              '#${color.toARGB32().toRadixString(16).substring(2).toUpperCase()}',
              style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}

class _SpacingSwatch extends StatelessWidget {
  const _SpacingSwatch({required this.size});
  final double size;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: size + 8,
          height: size + 8,
          decoration: BoxDecoration(
            color: NovaColors.primary.withValues(alpha: 0.18),
            borderRadius: BorderRadius.circular(4),
          ),
        ),
        const SizedBox(height: 4),
        Text('${size.toInt()}px', style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}

class _MotionPreviewPage extends StatelessWidget {
  const _MotionPreviewPage();

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Motion preview')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(NovaSpacing.xl),
            child: NovaFadeSlide(
              child: NovaCard(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.auto_awesome_rounded,
                        size: 48, color: NovaColors.primary),
                    const SizedBox(height: NovaSpacing.md),
                    Text('Smooth transitions',
                        style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: NovaSpacing.sm),
                    const Text(
                        'This page uses NovaPageRoute. System reduced-motion settings are respected.'),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
}
