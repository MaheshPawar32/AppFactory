# MyAppFactory v3.0 — Milestone 12: App Creation Wizard

## Purpose
Turn a few app decisions into a validated `APP_BRIEF.json`, an implementation plan and a Claude Code start prompt. The wizard prepares project instructions; it does not generate app source or call Claude.

## Quick start
Preview first:
```bash
python3 scripts/app_creation_wizard.py --name "Fit Track" --goal "Track daily fitness" --dry-run
```
Generate brief and plan:
```bash
python3 scripts/app_creation_wizard.py --name "Fit Track" --goal "Track daily fitness" \
  --features "daily log,reminders,progress charts" --screens "Home,Add Entry,History,Settings"
```
Files are created under `generated_briefs/fittrack/` by default. Existing output folders are not overwritten.

## Choose architecture and integrations
```bash
python3 scripts/app_creation_wizard.py --name "Spendwise" \
  --state-management Provider --storage Hive --backend none --locales en,hi,mr
```
Supported backend choices: `none`, `supabase`, `custom_api`, `firebase`. Firebase and AdMob are opt-in flags (`--firebase`, `--admob`). The wizard never creates credentials or configures external accounts.

## JSON input
Pass `--input /path/to/wizard_answers.json` to provide structured answers. The input may define `app`, `architecture`, `storage`, `integrations`, `design`, plus comma-separated `features`, `screens`, `locales`, and `target_users` fields.

## Outputs
- `APP_BRIEF.json`
- `IMPLEMENTATION_PLAN.json`
- `CLAUDE_CODE_START_PROMPT.md`

Open Claude Code at the intended Flutter project and review the prompt. Confirm architecture and integration setup before implementation.

## Safety
- `--dry-run` writes no files.
- Existing output directories are refused rather than overwritten.
- No app source is generated; no credentials are invented; no signing, upload or publishing occurs.
- Review the brief before giving it to an implementation agent.
