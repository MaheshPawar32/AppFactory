# Visual App Generation Workflow — v1.8

## Purpose
Turn an app idea and supplied UI reference images into a traceable screen plan, then implement in small, reviewable increments. This workflow is for Claude Code or another coding assistant working in the actual project folder.

## Phase 0 — Protect the project
1. Identify whether the project is new or existing.
2. Inspect the repository tree, `pubspec.yaml`, routing, state management, persistence, tests, and Git status.
3. For existing projects, create a Git commit or backup before substantial changes.
4. Record constraints and files that must not be changed.
5. Do not replace configuration, lockfiles, architecture or generated platform folders without a reason and explicit review.

## Phase 1 — Intake and reference inventory
1. Complete `templates/app_brief/APP_BRIEF_TEMPLATE.md`.
2. Create a reference index using `templates/project_docs/UI_REFERENCE_INDEX.md`.
3. Give every supplied image a stable ID (REF-001, REF-002...). Record filename, likely screen, important layout details, reusable patterns, and uncertainties.
4. If a reference is ambiguous or cropped, state the uncertainty rather than inventing details.
5. Reference images guide implementation; they must not be embedded as static screen backgrounds in the app.

## Phase 2 — Screen map and design contract
1. Create `SCREEN_INVENTORY.md` from `templates/project_docs/SCREEN_INVENTORY.md`.
2. Assign stable screen IDs (SCR-001...) and route names.
3. Define each screen's entry point, user goal, content hierarchy, primary action, secondary actions, data sources, loading/empty/error/offline states, accessibility requirements, and acceptance criteria.
4. Produce a navigation map and reusable-component inventory.
5. Define design tokens and responsive behavior before building screens.
6. Identify which parts of each reference are exact requirements and which are interpretation.

## Phase 3 — Build sequence
Implement vertical slices in this order, adapting to the app:
1. App shell, theme/tokens, routing and navigation.
2. Shared components and common loading/empty/error patterns.
3. Highest-value end-to-end user journey.
4. Remaining screens and edge states.
5. Persistence/backend integrations, permissions and notifications.
6. Accessibility, performance, localization and polish.

For each slice: state the files to change, implement only that slice, run the narrowest useful checks, inspect the diff, update the tracker, then proceed. Do not claim a test passed unless it was run.

## Phase 4 — Visual QA
For every screen:
- Compare the running UI with the reference at the same target viewport and text scale where possible.
- Check spacing, typography, color, alignment, hierarchy, overflow, safe areas, keyboard behavior, system bars and navigation.
- Check light/dark themes only if supported by the product.
- Check loading, empty, error, offline and permission states as applicable.
- Record mismatches and severity in `VISUAL_QA_LOG.md`.
- Use actual screenshots from the running app for evidence; a prompt or mockup is not runtime verification.

## Phase 5 — Acceptance and release
1. Map screen criteria to unit/widget/integration/manual tests.
2. Keep status labels separate: PLANNED, IN_PROGRESS, IMPLEMENTED, TESTED, BLOCKED, ACCEPTED.
3. `IMPLEMENTED` means code is present; `TESTED` means relevant checks were actually run; `ACCEPTED` means criteria and visual review were checked.
4. Record command output, device/OS, date, screenshot/log locations and known issues.
5. Use the Release Verification Record and Definition of Done before release.

## Required deliverables for each app
- `APP_BRIEF.md`
- `UI_REFERENCE_INDEX.md`
- `SCREEN_INVENTORY.md`
- `NAVIGATION_MAP.md`
- `COMPONENT_INVENTORY.md`
- `IMPLEMENTATION_PLAN.md`
- `PROGRESS_TRACKER.csv`
- `VISUAL_QA_LOG.md`
- `ACCEPTANCE_CRITERIA.md`
- `TEST_REPORT.md`
- `KNOWN_ISSUES.md`
- `RELEASE_RECORD.md`

## Existing-project safety rules
- Never delete or replace an existing app just to make it match the starter.
- Prefer small diffs over broad rewrites.
- Preserve state management and package choices unless the user approves a migration.
- Inspect generated changes before accepting them.
- Do not remove tests, disable analyzer rules globally, or weaken security to make checks pass.
- If the project is dirty or a change may be destructive, stop and explain the risk before proceeding.
