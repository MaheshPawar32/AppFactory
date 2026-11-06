#!/usr/bin/env python3
"""Compose MyAppFactory's brief, task controller, feature manifest and prompts safely."""
from __future__ import annotations
import argparse, json, re, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import app_creation_wizard as wizard
import app_generation_controller as controller
import ui_screen_generator as ui_generator

MODULE_RULES = {
    'onboarding': ('onboarding', 'basic'),
    'settings': ('settings_and_preferences', 'basic'),
    'offline_states': ('offline_storage', 'hive'),
    'local_notifications': ('local_notifications', 'scheduled'),
    'forms': ('forms_and_validation', 'reactive'),
    'forms_and_validation': ('forms_and_validation', 'reactive'),
    'api_client': ('api_client', 'rest'),
    'firebase': ('firebase_optional', 'selected'),
    'admob': ('admob_optional', 'selected'),
}

def slugify(value):
    return re.sub(r'[^a-z0-9]+', '', value.lower()) or 'myapp'

def make_manifest(brief):
    selected, seen = [], set()
    features = [str(x).strip().lower().replace(' ', '_') for x in brief.get('features', [])]
    integrations = brief.get('integrations', {})
    if brief.get('architecture', {}).get('storage', '').lower() == 'hive': features.append('offline_states')
    if integrations.get('firebase_enabled'): features.append('firebase')
    if integrations.get('admob_enabled'): features.append('admob')
    for feature in features:
        rule = MODULE_RULES.get(feature)
        if rule and rule[0] not in seen:
            module_id, choice = rule
            selected.append({'id': module_id, 'choice': choice, 'status': 'not configured', 'approved': False})
            seen.add(module_id)
    return {'schema_version': 1, 'app': {'name': brief['app']['name'], 'package_name': brief['app']['package_name'], 'path': 'NOT_ASSIGNED'}, 'selected_modules': selected,
            'notes': ['Selections are proposed only; no modules are installed by this workflow.', 'Optional integrations require explicit user approval and user-owned credentials.']}

def run(data, output_root, execute=False):
    brief = wizard.make_brief(data)
    plan = wizard.create_plan(brief)
    slug = brief['app']['slug']
    target = output_root.expanduser().resolve() / slug
    summary = {'status': 'DRY_RUN' if not execute else 'READY', 'app_name': brief['app']['name'], 'package_name': brief['app']['package_name'],
               'target': str(target), 'planned_outputs': ['APP_BRIEF.json', 'IMPLEMENTATION_PLAN.json', 'FEATURE_MODULES.json', 'workflow/workflow_state.json', 'workflow/prompts/*.md', 'SCREEN_INVENTORY.md', 'UI_DESIGN_PROMPTS.md', 'ui_references/', 'CLAUDE_CODE_UI_INSTRUCTIONS.md', 'CLAUDE_CODE_START_PROMPT.md'],
               'source_code_generated': False, 'claude_called': False, 'runtime_kit_installed': False, 'external_integrations_configured': False}
    if not execute:
        return summary
    if target.exists(): raise FileExistsError(f'Refusing to overwrite existing workflow: {target}')
    target.mkdir(parents=True, exist_ok=False)
    try:
        brief_path = target / 'APP_BRIEF.json'
        brief_path.write_text(json.dumps(brief, indent=2) + '\n', encoding='utf-8')
        (target / 'IMPLEMENTATION_PLAN.json').write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
        manifest = make_manifest(brief)
        (target / 'FEATURE_MODULES.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        ui_generator.generate(brief, target)
        workflow_dir = target / 'workflow'
        state = controller.initialize(workflow_dir, brief_path)
        for task in state['tasks']:
            (workflow_dir / 'prompts' / f"{task['id']}.md").write_text(controller.task_prompt(state, task), encoding='utf-8')
        start_prompt = f'''# MyAppFactory one-command workflow: {brief['app']['name']}\n\n1. Read `APP_BRIEF.json`, `IMPLEMENTATION_PLAN.json`, `FEATURE_MODULES.json`, `SCREEN_INVENTORY.md`, `UI_DESIGN_PROMPTS.md`, `UI_REFERENCE_INDEX.md`, `CLAUDE_CODE_UI_INSTRUCTIONS.md` and `workflow/workflow_state.json`.\n2. Inspect all available images in `ui_references/`; request missing references rather than assuming they exist.\n3. Start with `workflow/prompts/brief_review.md`; work one task at a time and complete every inventoried screen.\n3. Ask for explicit approval for architecture, integrations, credentials, permissions, and release preparation.\n4. Preserve existing work. Do not install modules or runtime kit unless requested and reviewed.\n5. Record actual evidence; mark unavailable checks NOT RUN. Never sign, publish, or invent secrets.\n\nUse the workflow controller to track progress. This package contains plans and prompts, not a generated Flutter app.\n'''
        (target / 'CLAUDE_CODE_START_PROMPT.md').write_text(start_prompt, encoding='utf-8')
        summary.update({'status': 'CREATED', 'ui_screen_count': len(json.loads((target / 'SCREEN_INVENTORY.json').read_text(encoding='utf-8'))['screens']), 'workflow_tasks': len(state['tasks']), 'feature_modules_proposed': len(manifest['selected_modules']), 'workflow_state': str(workflow_dir / 'workflow_state.json')})
        (target / 'WORKFLOW_SUMMARY.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
        return summary
    except Exception:
        # Keep partial output for inspection rather than deleting user-visible evidence.
        raise

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, help='JSON answers in the same format accepted by app_creation_wizard.py')
    p.add_argument('--name', help='App name')
    p.add_argument('--package', help='Optional package ID')
    p.add_argument('--goal', default='Describe the app\'s main purpose')
    p.add_argument('--features', default='onboarding,settings,offline_states')
    p.add_argument('--screens', default='Home,Settings')
    p.add_argument('--state-management', default='Provider', choices=('Provider','VelocityX','Riverpod','Bloc','GetX','None'))
    p.add_argument('--storage', default='Hive', choices=('Hive','SQLite','SharedPreferences','None'))
    p.add_argument('--backend', default='none', choices=('none','supabase','custom_api','firebase'))
    p.add_argument('--firebase', action='store_true'); p.add_argument('--admob', action='store_true')
    p.add_argument('--locales', default='en'); p.add_argument('--style', default='modern_premium')
    p.add_argument('--output', type=Path, default=ROOT/'generated_workflows')
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--execute', action='store_true', help='Write workflow files; requires a new output folder')
    mode.add_argument('--dry-run', action='store_true', help='Explicitly preview only; writes no files (default)')
    a = p.parse_args(argv)
    try:
        if a.input:
            data = json.loads(a.input.read_text(encoding='utf-8'))
        else:
            if not a.name: p.error('provide --name or --input')
            data = {'app': {'name': a.name, 'primary_goal': a.goal}, 'features': a.features, 'screens': a.screens,
                    'architecture': {'state_management': a.state_management}, 'storage': {'type': a.storage, 'offline_first': True},
                    'integrations': {'backend': a.backend, 'firebase_enabled': a.firebase, 'admob_enabled': a.admob},
                    'locales': a.locales, 'design': {'style': a.style}}
            if a.package: data['app']['package_name'] = a.package
        print(json.dumps(run(data, a.output, a.execute), indent=2)); return 0
    except (OSError, json.JSONDecodeError, ValueError, FileExistsError) as exc:
        print(json.dumps({'status': 'BLOCKED', 'error': str(exc)}, indent=2), file=sys.stderr); return 2

if __name__ == '__main__': raise SystemExit(main())
