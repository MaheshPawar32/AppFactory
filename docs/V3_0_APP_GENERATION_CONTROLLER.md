# MyAppFactory v3.0 — Milestone 2: App Generation Controller

## Purpose
Create a persistent task plan from an app brief, generate a focused Claude Code prompt for the next task, and record progress/evidence so the workflow can resume after interruptions. It does not directly call Claude or execute instructions contained in a brief.

## 1. Prepare an app brief
Copy `templates/project_docs/APP_BRIEF.json`, edit it, and save it outside any existing app workspace. Describe the app, screens, constraints, integrations and references. Do not put credentials or private user data in the brief.

## 2. Initialize a new workflow
```bash
python3 scripts/app_generation_controller.py init \
  --brief /path/to/APP_BRIEF.json \
  --workspace /path/to/workflows/my_app
```
The workspace must not already exist. Initialization creates `brief.json`, `workflow_state.json`, `prompts/` and `evidence/`; it does not generate app source.

## 3. Inspect and continue
```bash
python3 scripts/app_generation_controller.py status --workspace /path/to/workflows/my_app
python3 scripts/app_generation_controller.py next --workspace /path/to/workflows/my_app
python3 scripts/app_generation_controller.py next --workspace /path/to/workflows/my_app --output /path/to/task_prompt.md
```
Paste the generated task prompt into Claude Code opened at the actual Flutter project root. Review the output before recording completion.

## 4. Record work honestly
```bash
python3 scripts/app_generation_controller.py start --workspace /path/to/workflows/my_app --task brief_review
python3 scripts/app_generation_controller.py complete --workspace /path/to/workflows/my_app --task brief_review --evidence requirements_summary.md --evidence "Reviewed open questions with user"
python3 scripts/app_generation_controller.py block --workspace /path/to/workflows/my_app --task quality_tests --reason "Flutter SDK unavailable"
```
Completion requires at least one evidence entry. Evidence is recorded as supplied by the operator; the controller does not independently verify those paths or claims. Prefer real paths, command exit codes and logs.

## 5. Approval gates
Architecture decisions, integration setup and release preparation are gated. A human must explicitly approve them with a meaningful note before the next task prompt/start/completion can proceed:
```bash
python3 scripts/app_generation_controller.py approve --workspace /path/to/workflows/my_app --task architecture_review --note "Reviewed Provider + local storage architecture; proceed"
```
Approval records intent; it does not validate technical correctness or grant external account access.

## 6. Pause and resume
```bash
python3 scripts/app_generation_controller.py pause --workspace /path/to/workflows/my_app
python3 scripts/app_generation_controller.py pause --workspace /path/to/workflows/my_app --resume
```
The state file is saved after each state transition. Back it up with the workflow workspace. Do not hand-edit state unless you understand the schema.

## Safety boundaries
- Never overwrites an existing workflow workspace or prompt output file.
- Does not run arbitrary shell commands from the brief.
- Does not call Claude automatically; generated prompts are intended for review and paste into Claude Code.
- Does not publish, sign, change package identity or create credentials.
- The controller's status/evidence are workflow records, not proof that code works. Use `flutter_build_engine.py` to run real checks.
