# Milestone 14 — Reusable UI Screen Generator & Image-Reference Workflow

## What it adds
Every executed app workflow now creates:
- `SCREEN_INVENTORY.json` and `.md` from the app brief's screens plus sensible common screens.
- `UI_DESIGN_PROMPTS.md`, a screen-by-screen design brief and image export specification.
- `ui_references/`, with a README and per-screen reference instructions. Add the actual PNG/JPG files here.
- `UI_REFERENCE_INDEX.md` for mapping references to screens.
- `CLAUDE_CODE_UI_INSTRUCTIONS.md` and `UI_IMPLEMENTATION_STATUS.md`.

The one-command workflow includes these deliverables automatically. The dry-run reports planned outputs without writing files. Existing workflow folders remain protected from overwrite.

## Usage
```bash
python3 scripts/one_command_app_workflow.py --name "Fit Track" --goal "Track daily fitness" --screens "Home,Add activity,History,Statistics,Settings" --dry-run
python3 scripts/one_command_app_workflow.py --name "Fit Track" --goal "Track daily fitness" --screens "Home,Add activity,History,Statistics,Settings" --execute
```
Then add approved images to `generated_workflows/fittrack/ui_references/` using the exact filenames in `SCREEN_INVENTORY.json`. Open `UI_DESIGN_PROMPTS.md` in your image design workflow, and give `CLAUDE_CODE_START_PROMPT.md` plus `CLAUDE_CODE_UI_INSTRUCTIONS.md` to Claude Code.

## Honest boundaries
The generator creates inventories, prompts, indexes and folders. It does not render images, generate Flutter UI source, invoke Claude, automatically inspect image contents, or claim visual QA passed. Image generation/export and human design approval remain separate steps. Runtime screenshot comparison is still performed using the existing QA workflow.
