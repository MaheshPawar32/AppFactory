# Visual Regression Workflow (v1.9+)

## Goal
Compare a running Flutter app against approved reference screenshots without confusing a mockup, file presence, or a successful command with verified runtime behavior.

## Evidence workflow
1. Assign stable screen/reference IDs in `UI_REFERENCE_INDEX.md` and `SCREEN_INVENTORY.md`.
2. Record the device/emulator model, Android version, screen resolution, pixel density, text scale, theme, locale, system-bar mode and app build/commit.
3. Capture the reference and runtime screenshot at comparable dimensions and states. Do not compare different loading states or different content.
4. Store evidence under a project-local folder such as `qa/visual/<screen_id>/<date-or-commit>/`. Use descriptive names: `SCR-001_reference.png`, `SCR-001_runtime_pixel_1080x2400.png`, `SCR-001_diff.png`.
5. Record findings in `VISUAL_QA_LOG.md`, including evidence paths and status. Use `NOT RUN` when no runtime screenshot exists.
6. Review automated diffs manually. Dynamic timestamps, fonts, OS bars, anti-aliasing, shadows and network content can create false positives.

## Optional image comparison
- Pixel-level comparison is meaningful only when dimensions, scale, state and content are controlled.
- ImageMagick may be used optionally (`compare reference.png runtime.png diff.png`); it is not a required dependency.
- Do not treat a pixel-difference percentage as an automatic design-quality score. Set thresholds per screen and manually inspect differences.
- If comparison tooling is absent, report `NOT RUN`, not `PASS`.
- Never claim visual QA passed from a reference image alone.

## Acceptance
- Every critical screen has an identified reference or documented reason for no reference.
- Runtime screenshot evidence exists for each screen marked visually verified.
- High-severity differences have an owner, status and retest evidence.
- Evidence paths are relative to the project where practical and do not contain private user data.
