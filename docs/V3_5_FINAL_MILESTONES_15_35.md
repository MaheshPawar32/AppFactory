# MyAppFactory v3.5 — Final milestones 15–35

This release adds 21 runnable milestone tools on top of the preserved milestones 1–14. Run a milestone with:

```bash
python scripts/milestone_15.py --project /path/to/app
python scripts/milestone_35.py --project /path/to/app
```

Or run the shared engine directly:

```bash
python scripts/advanced_milestone_engine.py --milestone 21 --project /path/to/app
```

Each run writes a `MILESTONE_REPORT.json` and its outputs under `factory_reports/milestone_NN/` unless `--output` is supplied. Milestones are generators and evidence-oriented static checks, not autonomous coding agents. UI screen generation creates scaffolds, not complete production business logic. Backend/API outputs are contracts/checklists, not live credentials or connected services. Security/performance checks are heuristic. Release and Play Store tools prepare checklists/manifests; they do not sign, upload, publish or guarantee policy approval. Human review and actual Flutter/device verification remain required.

## Milestone catalog

| # | Milestone | Main output |
|---:|---|---|
| 15 | AI UI Design Workflow | Create design prompts, screen inventory and image-reference checklist. |
| 16 | Design System Generator | Generate color, typography, spacing and component tokens. |
| 17 | Flutter Screen Generator | Generate safe Flutter screen/navigation implementation scaffolds. |
| 18 | Automated UI Testing | Create widget-test plan, test templates and screenshot comparison manifest. |
| 19 | App Quality Intelligence | Run static project checks and produce a quality report. |
| 20 | Master Factory Dashboard | Aggregate registered apps and milestone evidence into JSON/HTML. |
| 21 | AI App Architecture Planner | Generate architecture, feature decomposition, data and navigation plans. |
| 22 | Backend & API Generator | Generate API contracts, Dart DTO/repository scaffolds and integration checklist. |
| 23 | Localization Manager | Generate ARB locale files and translation completeness reports. |
| 24 | App Update & Migration Manager | Track versions and create ordered migration plans. |
| 25 | Automated Documentation Generator | Generate README, architecture and release documentation. |
| 26 | AI Code Review | Run deterministic code-review heuristics and produce review findings. |
| 27 | Smart Bug Fix Engine | Classify diagnostics and create human-reviewed fix plans; never auto-apply. |
| 28 | App Security Scanner | Scan source/config for common secret and unsafe-pattern indicators. |
| 29 | Performance Optimizer | Find likely performance hotspots and provide actionable suggestions. |
| 30 | Device Compatibility Testing | Generate Android device/OS test matrix and capture evidence checklist. |
| 31 | Automated Release Manager | Prepare versioned release checklist and artifact manifest. |
| 32 | Play Store Readiness Checker | Check store listing assets/metadata and policy review checklist. |
| 33 | App Analytics Integration | Generate optional analytics event taxonomy and consent checklist. |
| 34 | Reusable App Template Library | Catalog, validate and package reusable app templates. |
| 35 | AI App Maintenance Assistant | Aggregate app health, stale reports, dependencies and maintenance actions. |
