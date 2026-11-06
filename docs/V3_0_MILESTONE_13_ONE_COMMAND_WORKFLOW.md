# MyAppFactory v3.0 — Milestone 13: One-Command App Generation Workflow

## Purpose
Compose the app creation wizard, generation controller, feature-module catalog and Claude Code prompt handoff into one resumable workflow workspace.

## Usage

Preview only (default; writes nothing; `--dry-run` is also accepted):

```bash
python3 scripts/one_command_app_workflow.py --name "Fit Track" --goal "Track daily fitness"
```

Create workflow files:

```bash
python3 scripts/one_command_app_workflow.py --name "Fit Track" --goal "Track daily fitness" --features "onboarding,settings,offline_states,local_notifications" --execute
```

Or pass a wizard-compatible JSON file:

```bash
python3 scripts/one_command_app_workflow.py --input app_answers.json --output generated_workflows --execute
```

The output directory contains `APP_BRIEF.json`, `IMPLEMENTATION_PLAN.json`, `FEATURE_MODULES.json`, `CLAUDE_CODE_START_PROMPT.md`, `WORKFLOW_SUMMARY.json`, and `workflow/` with controller state, evidence directory and per-task prompts.

## Resume and track

```bash
python3 scripts/app_generation_controller.py status --workspace generated_workflows/fittrack/workflow
python3 scripts/app_generation_controller.py next --workspace generated_workflows/fittrack/workflow
```

Use the exact workflow path printed by the wizard. The controller remains the source of task state and approval gates.

## Safety and limitations
- Default is a no-write dry run; `--execute` is required to create files.
- Existing output folders are never overwritten.
- It creates a workflow plan and prompts, **not Flutter application source**.
- It does not call Claude Code, run Flutter builds, install modules/runtime kit, configure accounts, generate credentials, sign, upload or publish.
- Feature modules are proposed from the brief and remain unconfigured until explicitly implemented and tested.
- Architecture, external integrations, and release preparation retain human approval gates.
