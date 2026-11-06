# Visual QA Guide

This guide describes how to verify UI rendering. Screenshot comparison is meaningful only when the device size, pixel ratio, font scale, theme, locale, and test data are controlled.

## Recommended workflow
1. Select critical screens and states from the screen inventory.
2. Add deterministic widget/golden tests for reusable components and stable screen regions.
3. Capture screenshots on the same test viewport and theme as the approved baseline.
4. Review golden diffs before accepting any baseline update.
5. Run integration tests on an emulator or device for navigation and real platform behavior.
6. Report visual checks as passed, failed, or not run based on actual output.

## Golden test practices
- Use deterministic fake data, fixed dates and stable fonts.
- Avoid capturing network images or live API results in golden tests.
- Keep one baseline per intentional theme/viewport where valuable.
- Never run automatic baseline updates just to silence failures; inspect the difference first.
- Treat golden tests as regression detection, not proof of usability or pixel-perfect matching on every device.

## Manual visual checklist
- [ ] No clipped or overflowing content.
- [ ] Buttons, text fields and navigation are visible and reachable.
- [ ] Long text and large font scale are handled.
- [ ] Empty, loading, error and offline states look intentional.
- [ ] Light/dark themes and localized text are checked where supported.
- [ ] Contrast, focus, semantic labels and touch targets are reviewed.
