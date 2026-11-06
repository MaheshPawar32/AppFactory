# MyAppFactory

Reusable Flutter app factory with Nova UI v1.2, reusable motion/loading/form/feedback components, quality checklists and a repeatable Claude workflow.

## Folder guide

- `design_system/nova_ui_flutter/` — the actual Nova UI Flutter source project.
- `templates/nova_ui_flutter_starter/` — a clean starter copy to duplicate for a new app.
- `prompts/master_app_prompt.md` — the reusable app-building master prompt.
- `prompts/firebase_admob_setup.md` — configuration questions for Firebase and AdMob.
- `references/` — design-system reference images and future app UI screenshots.
- `apps/` — put each actual app project in its own folder.
- `docs/` — project workflow and notes.

## Start using MyAppFactory

1. Extract this ZIP.
2. Install Flutter and open `design_system/nova_ui_flutter/` in VS Code or Android Studio.
3. Run `flutter pub get`, `flutter analyze`, `flutter test`, then `flutter run`.
4. For a new app, copy `templates/nova_ui_flutter_starter/` into `apps/<your_app_name>/`.
5. Open the new app folder in Claude Code.
6. Paste `prompts/master_app_prompt.md`, add the app idea and UI reference images, and answer the Firebase/AdMob questions.
7. Ask Claude to use Nova UI and implement the actual app, then run the test and release checklist.

## Important

The current validation evidence for the canonical design system and this workspace is recorded in [`docs/FINAL_FACTORY_READINESS_REPORT.md`](docs/FINAL_FACTORY_READINESS_REPORT.md). Re-run Flutter validation after changes and on the target app/device; a local debug build does not verify release signing, device behavior, or Play Store readiness. Firebase and AdMob are intentionally not configured by default.

## v1.3 additions
- Safe Claude/Git workflow and project change protection.
- GitHub Actions CI starter for format, analyze and test.
- Android release checklist, architecture guide and localization guide.
- `.gitignore` and placeholder-only `.env.example`.
- Detailed quality and release checklists.

Read `docs/V1_3_UPGRADE.md` before using the new workflow. CI and tests must be run in a real Flutter environment; this ZIP does not imply they have passed.

## v1.4 additions — Complete App Generation
- Pre-build decision engine and screen inventory.
- App starter profiles for offline utilities, productivity, fitness, content, API-driven, authentication, commerce and community apps.
- Optional feature module catalog and integration status tracking.
- UI reference workflow and screenshot comparison guidance.
- Expanded Claude master prompt to plan before coding and report verification honestly.

## v1.5 additions — Visual QA and Release Quality
- Visual QA and golden-test guidance.
- End-to-end testing guidance for critical user journeys.
- A Definition of Done for every app and feature.
- Performance/reliability guidance and component-library roadmap.
- Design-system versioning guide and template synchronization checker.

## v1.6 additions — Automation & Project Management
- Read-only structural project audit script.
- AI code-review and security/privacy checklists.
- Standard per-app deliverables and project documentation templates.
- Multi-app project registry CSV.
- UI showcase guide and CI audit step.

## v1.7 additions — Automation & Reliability

- Safe new-app workspace creation with `scripts/create_app.py` (`--dry-run` supported; existing destinations are never overwritten).
- Read-only Nova UI source/template update preview with optional unified diffs.
- Static dependency-risk inventory and optional `flutter pub outdated` execution when Flutter is installed.
- Acceptance-criteria-to-test mapping, explicit NOT RUN/PASS/FAIL/BLOCKED states, and a release verification record.
- Flutter/Android troubleshooting handbook and safe template update workflow.
- CI now syntax-checks Python scripts and runs the read-only template update preview.

### Create a new Android-ready app workspace

```bash
python3 scripts/create_app.py --name "Fit Track" --package com.dev.fittrack --target /tmp/fittrack --dry-run
python3 scripts/create_app.py --name "Fit Track" --package com.dev.fittrack --target /tmp/fittrack
cd /tmp/fittrack
flutter pub get
flutter analyze
flutter test
flutter build apk --debug --flavor development --dart-define=APP_ENV=development
```

The creator generates Android platform files using the installed Flutter SDK in an isolated temporary workspace, wires the Android namespace/application ID and Kotlin activity package, applies the app name and brand color, and adds development/staging/production flavors. It refuses to overwrite a target. `--dry-run` previews but does not write files. Use `--min-sdk` or `--target-sdk` only when your app has a verified platform requirement.

Development and staging Android IDs have `.dev` and `.staging` suffixes; production retains the requested package ID. Match the flavor with `--dart-define=APP_ENV=<environment>`. The generator does not configure release signing, Firebase/AdMob, production credentials, store artwork, or deployment. Review `APP_FACTORY_METADATA.md`, `APP_CONFIG.json`, and `STORE_ASSET_INVENTORY.json`; run Flutter checks before using the app.

To check feature-layer import boundaries, run `python3 scripts/architecture_audit.py /path/to/flutter-app`. `PARTIAL` means no recognized layered files were available for checking, not that architecture passed. APP_CONFIG v1 files can be migrated additively to a new file using `python3 scripts/validate_app_config.py APP_CONFIG.json --migrate-to-v2 --output APP_CONFIG.v2.json`; the migration refuses to overwrite.

### Preview design-system template updates

```bash
python3 scripts/template_update_preview.py --show-diff
python3 scripts/check_template_sync.py
```

The preview is read-only. It does not modify existing app projects. Port reviewed changes into each app deliberately and keep a backup/Git commit first.

### Dependency and release evidence

```bash
python3 scripts/dependency_audit.py apps/fittrack
python3 scripts/dependency_audit.py apps/fittrack --pub-outdated
```

The dependency script's static checks are only a risk inventory, not a vulnerability scan. `--pub-outdated` runs only when Flutter is installed. Use `templates/project_docs/ACCEPTANCE_CRITERIA.md`, `docs/ACCEPTANCE_TEST_WORKFLOW.md`, `templates/project_docs/RELEASE_RECORD_TEMPLATE.md`, and `templates/project_docs/DEPENDENCY_REVIEW.md` for each app.

The structural audit and Python checks do not prove that every generated Flutter app compiles, dependencies are secure, or a Play Store release is compliant. Run Flutter format/analyze/test/build and device checks in each actual app environment, and record observed results only.

## v1.8 additions — Visual App Generation Workflow

- Dedicated image-driven Claude prompt for screen planning and incremental Flutter implementation.
- App brief expanded to capture UI references, journeys, integrations and existing-project protection rules.
- Screen inventory, navigation map, component inventory, implementation plan and progress tracker templates.
- UI reference index and visual QA log for screenshot-based review.
- Workflow documentation from intake and screen mapping through implementation, QA and release.
- Clear status definitions to distinguish code implemented, tests executed and work accepted.

### Start a visual app project
1. Fill `templates/app_brief/APP_BRIEF_TEMPLATE.md`.
2. Attach reference screenshots to Claude Code and assign REF-001, REF-002, etc.
3. Use `prompts/visual_app_generation_prompt.md`.
4. Require the screen inventory and navigation plan before coding.
5. Implement one small milestone at a time and update `PROGRESS_TRACKER.csv`.
6. Compare runtime screenshots and record findings in `VISUAL_QA_LOG.md`.

For existing projects, inspect Git status and back up first. The workflow must preserve existing architecture and app-specific code; do not bulk-copy the starter over an existing app.


## v1.9 additions — Visual QA and device testing
- Screenshot evidence workflow and visual regression guidance.
- Device matrix for compact, typical, large, keyboard, enlarged-text, offline and permission scenarios.
- Accessibility review checklist and evidence-based statuses.

## v2.0 additions — Developer command center
- Read-only project dashboard for the app registry.
- Visual QA report for tracker and device-matrix completeness.
- Reusable feature recipes, recovery guidance and offline/failure-state test workflow.

## v2.1 additions — Safe automation and release readiness
- Central per-app `APP_CONFIG.yaml` template.
- Change impact and safe rollback workflow.
- Release readiness gates and asset/license inventory.
- CI smoke checks for the new read-only reports.
- Read-only release preflight helper for Flutter project setup and manual release gates.

## Use the new reports
From the MyAppFactory root, run `python3 scripts/project_dashboard.py` and `python3 scripts/visual_qa_report.py`. These scripts use Python's standard library. The visual report checks tracker completeness only; it does not compare screenshot pixels or verify runtime behavior.

## Verification limits
Python script checks, registry reports and structural audits do not prove that Flutter analysis, Dart tests, Android builds, device tests, accessibility or Play Store compliance passed. Run Flutter/device/release checks on a configured development machine and record their actual results.


## v2.2 additions — Consistency and testable tooling
- Machine-readable `APP_CONFIG.json` template and configuration validator.
- Project registry validation for required columns, duplicate names and explicit verification statuses.
- Asset/license inventory completeness report.
- Optional ImageMagick screenshot comparison helper with honest `NOT RUN` behavior when unavailable.
- Python unit tests for configuration, registry, asset inventory and screenshot helper failure paths.
- CI now runs the new unit tests and tool smoke checks.

### v2.2 commands
```bash
python3 scripts/validate_app_config.py templates/project_docs/APP_CONFIG.json
python3 scripts/validate_project_registry.py
python3 scripts/asset_license_report.py
python3 -m unittest discover -s tests -v
python3 scripts/screenshot_compare.py reference.png runtime.png --diff diff.png
```

The screenshot helper requires ImageMagick to be installed separately. A computed image difference is evidence for human review, not an automatic visual pass.


## v2.3–v2.5 additions — App validation, visual QA and consolidated checks

- Validate an actual Flutter app workspace with `python3 scripts/validate_flutter_project.py path/to/app --json`.
- Run the factory's standard checks together with `python3 scripts/run_factory_checks.py`; use `--strict` for a failing exit code when any selected check fails.
- Read `docs/V2_3_UPGRADE.md`, `docs/V2_4_UPGRADE.md`, `docs/V2_5_UPGRADE.md` and `docs/FACTORY_UPGRADE_ROADMAP.md`.
- Screenshot comparison remains optional and does not capture emulator screenshots by itself.

**Build status:** Factory structural checks do not build an Android APK/AAB. For each real app, run `flutter pub get`, `dart format --set-exit-if-changed .`, `flutter analyze`, `flutter test` and the appropriate APK/AAB build in a configured Flutter/Android environment. Only report success after observing each command's exit status.


## v3.0 — Build and recovery engine (Milestone 1)

The first v3.0 milestone adds a real command runner for an existing Flutter project:

```bash
python3 scripts/flutter_build_engine.py /path/to/flutter_app --dry-run
python3 scripts/flutter_build_engine.py /path/to/flutter_app --build apk
python3 scripts/flutter_build_engine.py /path/to/flutter_app --build appbundle
python3 scripts/flutter_build_engine.py /path/to/flutter_app --build none
```

The engine runs dependency resolution, formatting checks, static analysis, tests and (optionally) a release build. It writes per-command logs and a JSON report, verifies the expected APK/AAB exists, records Git working-tree snapshots, and applies only bounded recovery. Analyzer/test errors are reported for human/Claude Code repair rather than silently rewritten. Safe formatting recovery can modify Dart formatting; review the Git diff.

Read `docs/V3_0_BUILD_ENGINE.md` and `docs/V3_0_ROADMAP.md`. A real Android build requires Flutter and Android SDK installed on the machine running the command. A successful engine run is based on observed command exit codes and artifact checks, not a promise of Play Store approval.


## v3.0 — Milestone 2: App Generation Controller

The controller creates a resumable task plan from an app brief and generates focused prompts for Claude Code. It records progress, evidence, blockers, pause/resume state and human approval gates.

```bash
python3 scripts/app_generation_controller.py init --brief /path/to/APP_BRIEF.json --workspace /path/to/workflow
python3 scripts/app_generation_controller.py status --workspace /path/to/workflow
python3 scripts/app_generation_controller.py next --workspace /path/to/workflow
```

See `docs/V3_0_APP_GENERATION_CONTROLLER.md` and copy `templates/project_docs/APP_BRIEF.json` to begin. The controller does not call Claude automatically or generate app source; review its prompt and paste it into Claude Code.


## v3.0 — Milestone 3: Visual QA automation

Use `scripts/visual_qa_runner.py` to run Flutter tests and optionally capture the current screen from a connected Android device/emulator. It writes a JSON report and PNG evidence. Screenshot scenarios are supplied in `templates/project_docs/VISUAL_QA_MANIFEST.json`.

```bash
python3 scripts/visual_qa_runner.py /path/to/flutter_app --run-tests
python3 scripts/visual_qa_runner.py /path/to/flutter_app --manifest /path/to/VISUAL_QA_MANIFEST.json --capture
```

The runner does not automatically navigate the app or assert that a screen looks correct. Prepare the requested UI state before each capture and review the screenshots manually. Read `docs/V3_0_VISUAL_QA.md`.


## v3.0 Milestone 4 — Reusable Feature Modules

The opt-in module catalog includes offline storage, local notifications, onboarding, settings, forms, API clients, and optional Firebase/AdMob recipes. It validates choices and generates a focused Claude Code implementation brief without silently changing app source or adding dependencies.

```bash
python3 scripts/feature_module_manager.py list
python3 scripts/feature_module_manager.py validate templates/project_docs/FEATURE_MODULES.json
python3 scripts/feature_module_manager.py prompt templates/project_docs/FEATURE_MODULES.json --output apps/your_app/FEATURE_MODULE_IMPLEMENTATION_PROMPT.md
```

Read `docs/V3_0_MILESTONE_4_FEATURE_MODULES.md`. Update the example manifest before using it. The CLI does not implement app code or configure external services.


## v3.0 Milestone 5 — Reusable App Runtime Kit

Added dependency-free Dart primitives for result/error outcomes, async screen states and duplicate-action guarding. A conservative installer copies them into an existing Flutter app without editing dependencies or overwriting collisions by default.

```bash
python3 scripts/install_runtime_kit.py /path/to/flutter_app --json
```

See `docs/V3_0_MILESTONE_5_RUNTIME_KIT.md`. The kit still needs Dart/Flutter formatting, analysis and tests in the target app environment.


## v3.0 Milestone 6 — Quality Automation

Added read-only dependency review, Git change-impact recommendations, and evidence-based release preflight tools. These tools do not guarantee package compatibility or publish apps.

```bash
python3 scripts/dependency_compatibility_review.py apps/my_app --json
python3 scripts/change_impact_report.py apps/my_app --json
python3 scripts/release_readiness_preflight.py apps/my_app --json
```

See `docs/V3_0_MILESTONE_6_QUALITY_AUTOMATION.md`.


## v3.0 Milestone 7 — Multi-App Control Center

Track all registered apps in a JSON report or standalone responsive HTML dashboard. Update `apps/PROJECT_REGISTRY.csv` with real project paths, recorded check statuses, blockers and next actions.

```bash
python3 scripts/multi_app_control_center.py --json
python3 scripts/multi_app_control_center.py --html reports/control_center.html
```

See `docs/V3_0_MILESTONE_7_MULTI_APP_CONTROL_CENTER.md`. The dashboard is read-only and does not run Flutter checks.


## v3.0 Milestone 8 — Batch Build Pipeline

Orchestrate the existing Flutter build engine across registered apps. The pipeline defaults to dry-run, uses no build artifact by default, and never updates the registry unless explicitly requested.

```bash
python3 scripts/batch_build_pipeline.py
python3 scripts/batch_build_pipeline.py --execute --build none --fix-mode none
```

See `docs/V3_0_MILESTONE_8_BATCH_BUILD_PIPELINE.md`.


## v3.0 Milestone 9 — Build History & Release Artifact Manager

Index APK/AAB artifacts with SHA-256 fingerprints and discover factory build reports for a Flutter project.

```bash
python3 scripts/release_artifact_manager.py /path/to/flutter_project
python3 scripts/release_artifact_manager.py /path/to/flutter_project --record-history
```

History recording is opt-in. Signing is not verified and nothing is published. See `docs/V3_0_MILESTONE_9_RELEASE_ARTIFACT_MANAGER.md`.


## v3.0 Milestone 10 — Release Readiness Dashboard

Create a combined JSON/HTML view of registry statuses, discovered build reports and indexed artifacts.

```bash
python3 scripts/release_readiness_dashboard.py
python3 scripts/release_readiness_dashboard.py --json reports/release_readiness.json --html reports/release_readiness.html
```

The dashboard distinguishes recorded registry claims from evidence and never grants automatic publish readiness. See `docs/V3_0_MILESTONE_10_RELEASE_READINESS_DASHBOARD.md`.


## v3.0 Milestone 11 — Regression & Device QA Orchestrator

Run the Visual QA runner across registered projects, with dry-run default and optional screenshot capture.

```bash
python3 scripts/device_qa_orchestrator.py
python3 scripts/device_qa_orchestrator.py --execute
```

Screens must be prepared manually before screenshot capture. See `docs/V3_0_MILESTONE_11_DEVICE_QA_ORCHESTRATOR.md`.


## v3.0 Milestone 12 — App Creation Wizard

Generate a validated app brief, implementation plan and Claude Code start prompt from a few configuration choices.

```bash
python3 scripts/app_creation_wizard.py --name "Fit Track" --goal "Track daily fitness" --dry-run
python3 scripts/app_creation_wizard.py --name "Fit Track" --goal "Track daily fitness"
```

See `docs/V3_0_MILESTONE_12_APP_CREATION_WIZARD.md`. The wizard does not generate app source or configure external accounts.


## v3.0 Milestone 13 — One-Command App Generation Workflow

Preview a coordinated workflow without writing files (default; `--dry-run` is also accepted):

```bash
python3 scripts/one_command_app_workflow.py --name "Fit Track" --goal "Track daily fitness"
```

Create the app brief, plan, proposed feature manifest, resumable controller workspace and task prompts:

```bash
python3 scripts/one_command_app_workflow.py --name "Fit Track" --goal "Track daily fitness" --features "onboarding,settings,offline_states,local_notifications" --execute
python3 scripts/app_generation_controller.py status --workspace generated_workflows/fittrack/workflow
python3 scripts/app_generation_controller.py next --workspace generated_workflows/fittrack/workflow
```

See `docs/V3_0_MILESTONE_13_ONE_COMMAND_WORKFLOW.md`. This orchestrates planning and handoff only; it does not generate Flutter source, call Claude, install modules, configure services, sign, or publish. Existing output folders are not overwritten.


## v3.0 — Milestone 14: UI screen generator
Every executed one-command app workflow now creates a screen inventory, UI design prompt pack, image-reference folder, reference index, Claude Code UI instructions and implementation status tracker. See `docs/V3_0_MILESTONE_14_UI_SCREEN_GENERATOR.md`.

## Final roadmap: Milestones 1–35

MyAppFactory v3.5 includes the original milestones 1–14 plus runnable milestone tools 15–35. See `docs/V3_5_FINAL_MILESTONES_15_35.md` for the complete catalog, commands, outputs and limitations. Run `python3 -m unittest discover -s tests -v` for the Python factory test suite. Flutter/Dart builds require a configured Flutter SDK and Android toolchain; device tests require an Android device/emulator. The workspace's latest observed checks are recorded in [`docs/FINAL_FACTORY_READINESS_REPORT.md`](docs/FINAL_FACTORY_READINESS_REPORT.md).
