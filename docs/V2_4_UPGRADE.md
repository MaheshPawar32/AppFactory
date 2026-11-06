# MyAppFactory v2.4 — Visual Regression and Runtime Evidence

## Current capability
`scripts/screenshot_compare.py` optionally runs ImageMagick and creates a diff image plus a numeric metric. It deliberately reports `NOT RUN` if required inputs or the executable are missing.

## Recommended capture protocol
- Capture the same device size, Android version, font scale, locale, theme and app state.
- Use deterministic test data and disable or stabilize clocks, animations and network content where practical.
- Store reference screenshots with screen name, app version, device profile and capture date.
- Review the diff image manually. Numeric pixel differences are not a visual quality score.
- Keep screenshots free of real user data, tokens, personal notifications and account details.

## Limitations
This factory does not currently launch an emulator or capture screenshots automatically. Flutter integration/golden tests and device capture must run in an environment configured with Flutter and Android SDK.
