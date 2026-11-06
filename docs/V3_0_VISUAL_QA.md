# MyAppFactory v3.0 — Milestone 3: Visual QA Automation

## What is automated
- Runs `flutter test` on request.
- Runs additional manifest-provided test commands as argument arrays (no shell interpolation).
- Optionally captures the current screen of a connected Android device/emulator with `adb exec-out screencap -p`.
- Saves PNG evidence and a machine-readable `visual_qa_report.json`.
- Labels manual visual review as required; it does not claim screenshots are visually correct.

## Usage
```bash
# Run Flutter tests and save report
python3 scripts/visual_qa_runner.py /path/to/flutter_app --run-tests

# Capture screens (navigate app to each requested state manually first)
python3 scripts/visual_qa_runner.py /path/to/flutter_app \
  --manifest templates/project_docs/VISUAL_QA_MANIFEST.json --capture

# Run tests and capture using a specific connected device
python3 scripts/visual_qa_runner.py /path/to/flutter_app \
  --manifest /path/to/VISUAL_QA_MANIFEST.json --run-tests --capture --device emulator-5554
```

## Manifest format
- `test_commands`: array of command argument arrays, such as `["flutter", "test", "integration_test/app_test.dart"]`.
- `screenshots`: array of `{ "name": "safe_name", "description": "state description" }`.
- Capture names may contain letters, numbers, `_` and `-` only.
- The runner does not shell-evaluate manifest commands. Only use commands you trust.

## Capture requirements
- Install Android platform tools and ensure `adb devices` shows exactly one connected, unlocked device, or provide `--device`.
- Launch the app and navigate to the intended screen/state before each capture. The current runner captures the current display for each scenario; it does not reset, launch, or navigate the app.
- Use deterministic test data and consistent device dimensions, Android version, locale, font scale and theme.
- Keep reference screenshots separately and use `scripts/screenshot_compare.py` for optional image diff metrics.
- Avoid personal data and notifications in captures.

## Report interpretation
- `CAPTURED` means a PNG was written, not that its layout passed review.
- `EVIDENCE COLLECTED` means one or more test/capture actions completed; it is not an overall visual pass.
- `FAIL` means an invoked command or capture operation failed.
- `NOT RUN` means no test/capture evidence was requested or available.
- Manual visual and accessibility review remains required. The tool does not automatically identify overflow, contrast issues or tap-target defects.
