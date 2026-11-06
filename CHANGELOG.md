# MyAppFactory changelog

## v3.0.0 — Milestone 3
- Added Visual QA runner to execute Flutter tests and manifest-defined test commands.
- Added optional adb screenshot capture from a connected Android device/emulator, PNG evidence and JSON report.
- Added screenshot manifest template and visual QA workflow/manifest documentation.
- Added tests for missing-project safety and runner entry behavior.
- Explicitly preserves manual review; capture does not imply visual correctness and does not auto-navigate UI.

## v3.0.0 — Milestone 2
- Added resumable App Generation Controller driven by a JSON app brief.
- Added focused Claude Code task prompt generation, task progress, evidence, blocker and pause/resume records.
- Added explicit approval gates for architecture, integrations and release preparation.
- Added app brief template, controller documentation and acceptance checklist.
- Added tests for workflow initialization, existing-workspace protection and approval-gate defaults.

## v3.0.0 — Milestone 1
- Added Flutter build engine for dependency resolution, Dart format checks, static analysis, tests and optional APK/AAB release builds.
- Added bounded dependency/build retries, optional safe formatting recovery, command logs, JSON report and artifact verification.
- Added dry-run, environment detection, Git working-tree snapshots and explicit BLOCKED/FAIL/PASS statuses.
- Added v3.0 build-engine documentation, roadmap and unit tests.
- Build engine is not claimed to have produced an APK in environments without Flutter/Android SDK.


## v2.5.0
- Added consolidated factory check runner with JSON report and optional strict exit code.
- Added upgrade and evidence documentation for app validation, visual regression and release readiness.
- Clarified the boundary between factory checks and actual Flutter builds.

## v2.4.0
- Expanded screenshot comparison workflow with deterministic capture protocol, privacy guidance and manual review limitations.
- Documented the current boundary: screenshot capture/emulator automation is not included.

## v2.3.0
- Added read-only Flutter project structural validator for Android scaffolding, Gradle package metadata, permissions inventory and common safety flags.
- Added explicit review states and safe repair guidance; no project files are changed by the validator.

## v2.2.0
- Added machine-readable app config template and standard-library validator.
- Added project registry validation and asset/license inventory completeness reporting.
- Added optional ImageMagick screenshot comparison helper with explicit NOT RUN states.
- Added Python unit tests and CI smoke checks for new helper tools.
- Added v2.2 upgrade and usage documentation.


## v2.1.0
- Added safe automation and release-readiness gates with explicit preview/prepare/execute boundaries.
- Added per-app configuration manifest template, change-impact/rollback guidance, recovery workflow and asset-license inventory.
- Added release, permissions, secrets, signing, dependency, privacy and store-review checklist guidance.

## v2.0.0
- Added read-only developer dashboard for registered app stages, verification records, issues and next actions.
- Added visual QA tracker/device matrix report and CI smoke checks.
- Added reusable feature recipes and offline/failure-state testing guidance.

## v1.9.0
- Added screenshot-based visual regression workflow and runtime evidence naming.
- Added device/accessibility QA guide and device test matrix.
- Expanded visual QA log with reference/runtime evidence and retest fields.
## v1.8.0
- Added visual app-generation workflow from idea and reference images to screen inventory, navigation and implementation plan.
- Added dedicated Claude prompt for incremental implementation and existing-project protection.
- Added UI reference index, screen inventory, navigation map, component inventory and implementation plan templates.
- Added CSV progress tracker and visual QA log template.
- Expanded app brief for user journeys, visual constraints, integrations and acceptance requirements.

## v1.7.0
- Added safe app workspace creation CLI with dry-run and no-overwrite behavior.
- Added read-only Nova UI template update preview and optional unified diffs.
- Added static dependency-risk inventory and optional Flutter package-outdated command.
- Added acceptance criteria/test mapping, dependency review, release verification record and troubleshooting handbook.
- Added Python script syntax check and template preview to CI.

## v1.6.0
- Added read-only project audit script and CI audit step.
- Added AI code review and security/privacy audit guides.
- Added standard per-app deliverables and documentation templates.
- Added project registry CSV and UI showcase guide.


## v1.5.0
- Added visual QA, golden testing and end-to-end testing guides.
- Added app-wide Definition of Done and performance/reliability checklist.
- Added design-system versioning guidance and template synchronization checker.
- Added component library roadmap and CI sync check.


## v1.4.0
- Added complete app-generation planning workflow and screen inventory template.
- Added selectable starter profiles and optional feature-module catalog.
- Added UI reference mapping and visual comparison workflow.
- Expanded the master prompt with pre-build planning and integration verification states.


## v1.3.0
- Added safe Claude/Git workflow guidance.
- Added Android release checklist and reusable architecture/localization guides.
- Added a starter GitHub Actions workflow for formatting, analysis and tests.
- Added root ignore rules and a non-secret environment example.
- Added app quality and release checklists.

## v1.2.0
- Added shared form field, feedback, responsive layout, semantic icon button and brand theme helpers.
- Added guidance for localization, offline UX, QA gates, versioning and safe AI-assisted edits.


## v3.0 — Milestone 4 (Reusable Feature Modules)
- Added eight opt-in module recipes with dependency guidance and acceptance criteria.
- Added feature-module manifest validation and Claude Code prompt generation CLI.
- Added module status/evidence validation and unit tests.
- Updated documentation, project audit requirements and CI smoke checks.


## v3.0.0 — Milestone 5 (Reusable App Runtime Kit)
- Added dependency-free Dart result/failure, async-state and safe-action primitives.
- Added conservative runtime-kit installer with project validation and overwrite protection.
- Added installer tests and runtime-kit integration documentation.
- No dependencies or application screens are changed automatically.


## v3.0.0 — Milestone 6 (Quality Automation)
- Added read-only dependency compatibility review for pubspec manifests.
- Added Git-based/explicit-file change-impact reports with recommended regression checks.
- Added evidence-based release preflight with optional format/analyze/test commands.
- Added tests, example manifest, CI syntax checks and workflow documentation.


## v3.0.0 — Milestone 7 (Multi-App Control Center)
- Added registry-driven project health summary and responsive standalone HTML dashboard.
- Added app status, path, blockers, next action, and evidence fields in the project registry.
- Added safe HTML escaping, dashboard tests, documentation and structural audit coverage.
- Dashboard does not execute project code or claim registry statuses are independently verified.


## v3.0.0 — Milestone 8 (Batch Build Pipeline)
- Added registry-driven multi-app orchestration around the existing Flutter build engine.
- Added project-path preflight, dry-run default, per-app reports and explicit opt-in registry updates.
- Kept artifact builds, safe formatting recovery and execution opt-in.
- Added tests, documentation, CI smoke checks and structural audit coverage.


## v3.0.0 — Milestone 9 (Build History & Release Artifact Manager)
- Added APK/AAB artifact indexing with SHA-256 checksums and file metadata.
- Added discovery of build-engine reports and a local JSONL artifact history.
- Made history recording explicit and retained NOT CHECKED/NOT PUBLISHED safety statuses.
- Added unit tests, usage documentation and structural audit coverage.


## v3.0.0 — Milestone 10 (Release Readiness Dashboard)
- Added unified JSON/HTML dashboard for registry statuses, engine reports and indexed APK/AAB artifacts.
- Added evidence-based statuses that do not infer signing or publish readiness from registry claims.
- Added path/manifest blockers, artifact existence checks, HTML escaping, tests and documentation.


## v3.0.0 — Milestone 11 (Regression & Device QA Orchestrator)
- Added registry-driven orchestration around the existing Visual QA runner.
- Added dry-run default, per-app QA summaries and optional Android screenshot capture.
- Added project preflight, unknown-app validation, docs, CI smoke checks and unit tests.
- Preserved manual UI-state preparation and human visual review.


## v3.0.0 — Milestone 12 (App Creation Wizard)
- Added validated brief generation from CLI options or JSON input.
- Added architecture/storage/integration choices, implementation plan and Claude Code start prompt.
- Added safe dry-run, package ID validation, no-overwrite behavior, docs, tests and audit coverage.


## v3.0.0 — Milestone 13 (One-Command App Generation Workflow)
- Added a single orchestrator connecting validated app briefs, resumable controller tasks, proposed feature modules and Claude Code prompts.
- Added default dry-run, explicit `--execute`, no-overwrite protection and workflow summary evidence.
- Added milestone documentation, README usage, project audit coverage and tests.
- Kept source generation, Claude execution, runtime-kit installation, external integrations, signing and publishing outside the automated workflow.

## v3.0.0 — Integrated Milestones 1–13 verification
- Re-ran the complete Python unit-test suite across the factory tools; all 47 tests pass.
- Re-ran the consolidated strict factory checks; all 9 checks pass, including registry/config validation, template sync, dashboards, visual QA report generation and structural audit.
- Exercised Milestone 13 end-to-end in a temporary directory; it created the app brief, plan, feature manifest, controller state and nine resumable task entries without modifying a real Flutter app.
- Added explicit `--dry-run` support to the Milestone 13 CLI while preserving dry-run as the default, plus tests preventing simultaneous `--execute` and `--dry-run`.
- Python syntax compilation passed for all scripts and tests.
- Flutter/Dart were unavailable in this environment; no Flutter analyze/test, Android device QA, APK/AAB build, signing or publishing is claimed.


## v3.0.0 — Milestone 14 (Reusable UI Screen Generator & Image-Reference Workflow)
- Added screen inventory and per-screen design prompt generation from each app brief.
- Added UI reference image folder structure, reference index and implementation status tracker.
- Integrated UI deliverables into the one-command workflow and Claude Code start instructions.
- Added explicit boundaries: image files and Flutter source are not generated automatically; missing references remain clearly marked.

## v3.5 — Final release (Milestones 15–35)
- Added 21 milestone runners backed by an evidence-oriented generation engine.
- Added UI design workflow, design tokens, screen scaffolds, UI test plans, quality/security/performance heuristics, architecture/API/localization/migration/documentation generators, code review and bug-fix planning, device matrix, release/store preflight, analytics plan, template catalog and maintenance dashboard.
- Added tests covering all 21 milestone generators and a security-scan detection case.
- Preserved milestones 1–14.
- Python factory suite: 51 tests passed. Flutter/Dart build and device validation require a Flutter-enabled environment and were not represented as passed.
