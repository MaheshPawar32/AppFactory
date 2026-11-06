# MyAppFactory v3.0 roadmap

## Milestone 1 — Build and recovery engine (included)
- Preflight checks and explicit BLOCKED states.
- Dependency resolution, formatting, analysis, tests and APK/AAB release build.
- Bounded retries for dependency resolution and build.
- Optional safe formatting recovery with a clear source-modification warning.
- Per-command logs, JSON report, artifact existence/size check and Git snapshots.
- Dry-run support and honest status semantics.

## Milestone 2 — App generation controller
- App brief -> screen inventory -> architecture plan -> implementation tasks.
- Persisted workflow state and resumable task queue.
- Human approval gates for destructive or account-connected operations.
- Claude Code instructions that request evidence and never fabricate success.

## Milestone 3 — Visual QA
- Deterministic emulator/device screenshot capture.
- Flutter golden/integration test orchestration and diff artifact indexing.
- Screen overflow/accessibility smoke checks with manual-review status preserved.

## Milestone 4 — Reusable feature recipes
- Versioned modules for offline storage, local notifications, settings, onboarding, forms, API clients, authentication and optional Firebase/AdMob.
- Compatibility and license metadata for each module.
- App-specific migration, retry and duplicate-submission tests.

## Milestone 5 — Multi-app orchestration and release evidence
- Registry-driven app queue and consolidated dashboard.
- Build matrix, artifact checksums, version/commit metadata and release evidence bundle.
- Optional CI integration; never auto-publish or sign without explicit configuration and approval.

## Acceptance criteria for v3.0
- A real Flutter app can be passed to the engine and produce a report based on actual command results.
- Missing toolchain is clearly BLOCKED, not reported as a failed app build or a success.
- Failure recovery is bounded and does not delete user data or auto-edit business logic.
- APK/AAB success requires both a successful build command and the expected artifact on disk.
- Python unit tests pass and the ZIP passes integrity verification.
