# Nova UI Design System v1.0

## Principles

1. Clarity before decoration.
2. Consistent tokens instead of repeated arbitrary values.
3. Accessible interaction targets and scalable text.
4. Lightweight motion with no unnecessary delays.
5. Components are reusable and app-agnostic.

## Tokens

### Brand
- Primary: `#6366F1`
- Primary light: `#818CF8`
- Primary dark: `#4F46E5`
- Secondary: `#06B6D4`
- Success: `#10B981`
- Warning: `#F59E0B`
- Error: `#EF4444`
- Info: `#3B82F6`

### Spacing
`2, 4, 8, 12, 16, 24, 32, 48, 64` logical pixels.

### Radius
`8, 12, 16, 24` logical pixels; pill radius for chips and fully rounded controls.

### Typography
Roboto system fallback is used so the starter works offline. The design roles are display, headline, title, body, body-small, and caption. You can bundle another licensed font if desired.

## Components

- `NovaButton`: primary, secondary, outline, and text variants; loading state; optional icon.
- `NovaCard`: card surface with optional header and tap behavior.
- `NovaStatusBanner`: success, warning, error, and info states.
- `NovaSkeleton`: animated placeholder for loading content.
- `NovaTheme`: centralized Material 3 light/dark themes.

## Accessibility

- Keep interactive controls at least 48 logical pixels high where practical.
- Use semantic labels for icon-only controls.
- Support system text scaling.
- Check contrast in every theme.
- Do not communicate state through color alone.
- Provide a visible error message and recovery action for recoverable failures.

## App-specific branding

Override the color tokens and add app-specific components without changing generic component behavior. Avoid adding domain logic to this package.

New apps can create light and dark Material 3 themes from a reviewed brand seed:

```dart
theme: NovaBrandTheme.light(const Color(0xFF6366F1)),
darkTheme: NovaBrandTheme.dark(const Color(0xFF6366F1)),
```

Check text and semantic-color contrast after selecting a seed. Generated default
colors are scaffolding, not approved app artwork or an accessibility sign-off.


## Motion and loading (v1.1)

### Timing tokens
- Instant: 100 ms
- Fast: 150 ms
- Standard: 220 ms
- Medium: 280 ms
- Page: 320 ms
- Feedback: 360 ms
- Shimmer cycle: 1200 ms

Use these as starting defaults, not rigid rules. Avoid artificial waiting when data is ready. Respect `MediaQuery.disableAnimations`.

### Motion utilities
- `NovaFadeSlide`: fades and slightly translates content into view.
- `NovaPressable`: restrained scale feedback for tappable surfaces.
- `NovaAnimatedNumber`: animates a numeric value.
- `NovaPageRoute`: fade/slide route transition.

### Loading and states
- `NovaLoadingIndicator`: inline progress with optional label.
- `NovaFullScreenLoading`: centered full-area loading.
- `NovaSkeletonListTile`: reusable list placeholder.
- `NovaLoadingAction`: loading state for action buttons.
- `NovaEmptyState`: empty state with optional action.
- `NovaErrorState`: error/offline state with optional retry.

Always show loading indicators only while work is pending, provide recovery for errors, and avoid flashing skeletons for instantly available content.
