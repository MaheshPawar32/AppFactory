# MyAppFactory upgrade coverage: v2.3–v4.0

| Area | Coverage | Limitation |
|---|---|---|
| App/platform scaffold validation | v2.3 validator | Structural checks only; no automatic repair |
| Package/namespace inspection | v2.3 validator | Conservative Gradle text parser; manual review required |
| Permissions and cleartext review prompts | v2.3 validator | Does not inspect merged manifests or every plugin |
| Screenshot comparison | Existing v2.2 helper + v2.4 workflow | ImageMagick optional; no emulator capture |
| Consolidated factory checks | v2.5 runner | Runs factory checks, not Flutter builds |
| Unit tests | Existing tests + new cases | Python helper tests only |
| Data migration / backup safety | Existing workflow guidance | App-specific migration tests must be implemented per app |
| Offline retry / duplicate submissions | Existing testing guidance | Requires app-specific API/storage tests |
| Performance profiling / accessibility | Existing QA guides | Requires Flutter/device execution |
| Release signing / Play compliance | Existing checklists | Must be verified for each actual app |
| v3.0 workflow tools (milestones 1–14) | Build, generation, QA, dashboard and release helpers | Follow each tool's explicit execution and approval gates |
| v3.5 workflow tools (milestones 15–35) | Advanced milestone engine and report generators | Heuristic plans/reports do not replace app implementation or human review |
| v4.0 Batch 1 (milestones 36–40) | Android-aware app creation, app branding/store inventory, environment flavors, APP_CONFIG v2 migration, static architecture boundary audit | Review [V4.0 Batch 1](./V4_0_MILESTONES_36_40.md); generated apps still require Flutter/device validation and manual release gates |
| v4.0 Batch 3 (milestones 45–49) | Project-scoped test discovery/execution, Android compatibility/device evidence, accessibility heuristics, profile-build size evidence, dependency/license inventory and CycloneDX SBOM | `scripts/quality_qa_engine.py`; see [V4.0 Quality QA Engine](./V4_0_QUALITY_QA_ENGINE.md). Device, manual accessibility, profiling and CVE checks remain explicitly unverified unless executed |

## Honest build status
A Flutter Android APK/AAB build is claimed only when Flutter and the Android SDK are installed and the actual app project is built successfully. For the latest observed workspace results, including the debug APK evidence and checks that remain manual, see [FINAL_FACTORY_READINESS_REPORT.md](./FINAL_FACTORY_READINESS_REPORT.md).

For detailed milestone scope and command examples, see [V3_0_ROADMAP.md](./V3_0_ROADMAP.md) and [V3_5_FINAL_MILESTONES_15_35.md](./V3_5_FINAL_MILESTONES_15_35.md).
