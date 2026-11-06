#!/usr/bin/env python3
"""Evidence-oriented implementation helpers for MyAppFactory milestones 15–35."""
from __future__ import annotations
import argparse, json, re, hashlib, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
MILESTONES={
15:('AI UI Design Workflow','Create design prompts, screen inventory and image-reference checklist.'),
16:('Design System Generator','Generate color, typography, spacing and component tokens.'),
17:('Flutter Screen Generator','Generate safe Flutter screen/navigation implementation scaffolds.'),
18:('Automated UI Testing','Create widget-test plan, test templates and screenshot comparison manifest.'),
19:('App Quality Intelligence','Run static project checks and produce a quality report.'),
20:('Master Factory Dashboard','Aggregate registered apps and milestone evidence into JSON/HTML.'),
21:('AI App Architecture Planner','Generate architecture, feature decomposition, data and navigation plans.'),
22:('Backend & API Generator','Generate API contracts, Dart DTO/repository scaffolds and integration checklist.'),
23:('Localization Manager','Generate ARB locale files and translation completeness reports.'),
24:('App Update & Migration Manager','Track versions and create ordered migration plans.'),
25:('Automated Documentation Generator','Generate README, architecture and release documentation.'),
26:('AI Code Review','Run deterministic code-review heuristics and produce review findings.'),
27:('Smart Bug Fix Engine','Classify diagnostics and create human-reviewed fix plans; never auto-apply.'),
28:('App Security Scanner','Scan source/config for common secret and unsafe-pattern indicators.'),
29:('Performance Optimizer','Find likely performance hotspots and provide actionable suggestions.'),
30:('Device Compatibility Testing','Generate Android device/OS test matrix and capture evidence checklist.'),
31:('Automated Release Manager','Prepare versioned release checklist and artifact manifest.'),
32:('Play Store Readiness Checker','Check store listing assets/metadata and policy review checklist.'),
33:('App Analytics Integration','Generate optional analytics event taxonomy and consent checklist.'),
34:('Reusable App Template Library','Catalog, validate and package reusable app templates.'),
35:('AI App Maintenance Assistant','Aggregate app health, stale reports, dependencies and maintenance actions.')}

def write(p, content):
 p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content,encoding='utf-8'); return str(p)
def jread(p, default=None):
 try:return json.loads(Path(p).read_text(encoding='utf-8'))
 except (OSError,ValueError):return default

def run(n, project, output=None, extra=None):
 project=Path(project).resolve(); out=Path(output).resolve() if output else project/'factory_reports'/f'milestone_{n:02d}'
 out.mkdir(parents=True,exist_ok=True); files=[]; findings=[]
 brief=jread(project/'APP_BRIEF.json',{}) or {}; app=brief.get('app',{}); name=app.get('name',project.name)
 if n==15:
  from ui_screen_generator import generate
  generate(brief,out); files += ['SCREEN_INVENTORY.json','SCREEN_INVENTORY.md','UI_DESIGN_PROMPTS.md','UI_REFERENCE_INDEX.md','CLAUDE_CODE_UI_INSTRUCTIONS.md','UI_IMPLEMENTATION_STATUS.md']
 elif n==16:
  cfg=(brief.get('design') or {}); colors=cfg.get('colors',{'primary':'#6750A4','secondary':'#625B71','surface':'#FFFBFE','error':'#B3261E'})
  tokens={'app':name,'colors':colors,'typography':{'display':'32sp','headline':'24sp','title':'20sp','body':'16sp','label':'14sp'},'spacing':{'xs':4,'sm':8,'md':16,'lg':24,'xl':32},'radius':{'small':8,'medium':16,'large':24},'touch_target_min_dp':48}
  write(out/'DESIGN_TOKENS.json',json.dumps(tokens,indent=2)+'\n'); write(out/'DESIGN_SYSTEM.md','# Design system\n\n```json\n'+json.dumps(tokens,indent=2)+'\n```\n'); files+=['DESIGN_TOKENS.json','DESIGN_SYSTEM.md']
 elif n==17:
  inv=jread(project/'SCREEN_INVENTORY.json',{'screens':[]}) or {'screens':[]}; screens=inv.get('screens',[]); lib=out/'lib'/'generated_screens'
  for s in screens:
   sid=re.sub(r'[^a-z0-9_]+','_',s.get('id','screen').lower()).strip('_') or 'screen'; cls=''.join(x.title() for x in sid.split('_'))+'Screen'
   write(lib/f'{sid}_screen.dart',f"import 'package:flutter/material.dart';\n\nclass {cls} extends StatelessWidget {{\n  const {cls}({{super.key}});\n  @override Widget build(BuildContext context) => Scaffold(\n    appBar: AppBar(title: const Text('{s.get('name','Screen')}')),\n    body: const Center(child: Text('Implement approved {s.get('name','Screen')} experience')),\n  );\n}}\n")
  write(out/'NAVIGATION_PLAN.md','# Navigation plan\n\n'+'\n'.join(f"- `{s.get('id')}` — {s.get('name')}" for s in screens)+'\n'); files+=['lib/generated_screens/','NAVIGATION_PLAN.md']; findings.append('Generated scaffolds only; wire routes and business logic after review.')
 elif n==18:
  inv=jread(project/'SCREEN_INVENTORY.json',{'screens':[]}) or {'screens':[]}; tests=[]
  for s in inv.get('screens',[]): tests.append({'screen':s.get('id'),'test_file':f"test/{s.get('id')}_screen_test.dart",'cases':['renders without exception','primary action works','loading/empty/error states','accessibility labels']})
  write(out/'UI_TEST_PLAN.json',json.dumps({'tests':tests,'golden_tests':'manual approval required'},indent=2)+'\n'); write(out/'SCREENSHOT_MANIFEST.json',json.dumps({'screens':tests,'capture':'flutter test / device_qa_orchestrator','comparison':'manual review required'},indent=2)+'\n'); files+=['UI_TEST_PLAN.json','SCREENSHOT_MANIFEST.json']
 elif n==19 or n==26 or n==28 or n==29:
  exts={'.dart','.yaml','.yml','.json','.gradle','.xml'}; source=list(project.rglob('*')); source=[p for p in source if p.is_file() and any(x in p.parts for x in ('lib','android','test')) and p.suffix in exts and 'build' not in p.parts]
  for p in source:
   try:t=p.read_text(encoding='utf-8',errors='ignore')
   except OSError:continue
   checks=[]
   if n in (19,26) and 'TODO' in t: checks.append(('TODO','Review unfinished implementation'))
   if n in (19,26) and re.search(r'catch\s*\([^)]*\)\s*\{\s*\}',t): checks.append(('EMPTY_CATCH','Handle or log swallowed errors'))
   if n==28:
    for pat,label in [(r'(?i)(api[_-]?key|secret|password)\s*[:=]\s*["\'][^"\']{8,}', 'Possible hard-coded secret'),(r'http://(?!localhost)', 'Cleartext HTTP URL'),(r'allowBackup="true"','Android backup enabled; review sensitive-data exposure')]:
     if re.search(pat,t): checks.append(('SECURITY',label))
   if n==29:
    for pat,label in [(r'\bsetState\s*\(', 'Review rebuild scope and widget decomposition'),(r'\.toList\(\)\s*\.map\(', 'Review repeated collection allocation'),(r'Image\.network\(', 'Consider caching, placeholders and error handling')]:
     if re.search(pat,t): checks.append(('PERFORMANCE',label))
   findings += [{'file':str(p.relative_to(project)),'code':c,'recommendation':r} for c,r in checks]
  report={'milestone':n,'files_scanned':len(source),'findings':findings,'limitations':'Heuristic review only; not a substitute for expert review or platform scanners.'}
  write(out/'QUALITY_REPORT.json',json.dumps(report,indent=2)+'\n'); files+=['QUALITY_REPORT.json']
 elif n==20 or n==35:
  registry=project/'apps'/'PROJECT_REGISTRY.csv'; rows=[]
  if registry.exists():
   import csv
   with registry.open(encoding='utf-8-sig', newline='') as csv_file:
    rows = list(csv.DictReader(csv_file))
  data={'generated_at':datetime.now(timezone.utc).isoformat(),'milestone':n,'registered_apps':len(rows),'apps':rows,'factory_milestones':{str(k):v[0] for k,v in MILESTONES.items()},'note':'Registry status is recorded metadata, not independently verified test/build evidence.'}
  write(out/'FACTORY_HEALTH.json',json.dumps(data,indent=2)+'\n')
  html='<!doctype html><meta charset="utf-8"><title>MyAppFactory Health</title><h1>MyAppFactory Health</h1><p>Registered apps: '+str(len(rows))+'</p><pre>'+json.dumps(data,indent=2)+'</pre>'
  write(out/'FACTORY_HEALTH.html',html); files+=['FACTORY_HEALTH.json','FACTORY_HEALTH.html']
 elif n==21:
  features=brief.get('features',[]); screens=brief.get('screens',[])
  data={'app':name,'architecture':brief.get('architecture',{}),'features':features,'screens':screens,'layers':['presentation','application','domain','data'],'decisions_required':['state management','local persistence','backend/authentication','offline behavior','error handling','navigation']}
  write(out/'ARCHITECTURE_PLAN.json',json.dumps(data,indent=2)+'\n'); write(out/'ARCHITECTURE_PLAN.md','# Architecture plan\n\n'+json.dumps(data,indent=2)+'\n'); files+=['ARCHITECTURE_PLAN.json','ARCHITECTURE_PLAN.md']
 elif n==22:
  api={'base_url':'YOUR_API_BASE_URL','authentication':'Define auth strategy before use','endpoints':[],'models':[],'error_contract':{'code':'string','message':'string','retryable':'boolean'}}
  write(out/'API_CONTRACT.json',json.dumps(api,indent=2)+'\n'); write(out/'API_INTEGRATION_CHECKLIST.md','# API integration checklist\n\n- [ ] Confirm provider, base URL and commercial rights\n- [ ] Define authentication and token storage\n- [ ] Define request/response schemas\n- [ ] Add timeouts, retries and error mapping\n- [ ] Add mock tests and integration tests\n- [ ] Never commit credentials\n'); files+=['API_CONTRACT.json','API_INTEGRATION_CHECKLIST.md']
 elif n==23:
  locales=(brief.get('design') or {}).get('locales',['en']); locales=locales or ['en']; keys={'appName':name,'homeTitle':'Home','settingsTitle':'Settings'}
  for loc in locales:
   loc=str(loc).replace('-','_'); write(out/f'l10n/app_{loc}.arb',json.dumps({'@@locale':loc,**keys},ensure_ascii=False,indent=2)+'\n')
  write(out/'LOCALIZATION_REPORT.md','# Localization report\n\nGenerated keys are starter English values. Translate and review every locale before release.\n'); files+=['l10n/','LOCALIZATION_REPORT.md']
 elif n==24:
  v=(app.get('version') or '1.0.0+1'); data={'current_version':v,'migrations':[],'rules':['Never run destructive migrations without backup and approval','Migrations must be ordered and idempotent','Test upgrade from every supported prior schema']}
  write(out/'MIGRATION_PLAN.json',json.dumps(data,indent=2)+'\n'); files+=['MIGRATION_PLAN.json']
 elif n==25:
  write(out/'APP_README.md',f'# {name}\n\n{app.get("primary_goal", "Application overview pending.")}\n\n## Setup\n\n1. Install Flutter SDK.\n2. Run `flutter pub get`.\n3. Run `flutter analyze` and `flutter test`.\n4. Configure integrations using local secrets; never commit credentials.\n\n## Release\n\nSee `RELEASE_CHECKLIST.md`.\n')
  write(out/'ARCHITECTURE.md','# Architecture\n\nDocument approved layers, state management, storage, integrations, data flow and failure handling here.\n')
  write(out/'RELEASE_CHECKLIST.md','# Release checklist\n\n- [ ] Analyze and tests pass\n- [ ] Verify app ID/version/signing\n- [ ] Review permissions/privacy/data safety\n- [ ] Test release build on physical devices\n- [ ] Review store listing and policy declarations\n'); files+=['APP_README.md','ARCHITECTURE.md','RELEASE_CHECKLIST.md']
 elif n==27:
  write(out/'BUG_FIX_PLAN.md','# Human-reviewed bug fix plan\n\nFor each diagnostic, record reproduction steps, expected/actual behavior, root-cause hypothesis, proposed minimal fix, regression test and rollback. No source files are modified automatically.\n'); files+=['BUG_FIX_PLAN.md']
 elif n==30:
  matrix={'android_versions':['minimum_supported','latest_stable'],'screen_classes':['small_phone','standard_phone','large_phone','tablet'],'conditions':['fresh_install','upgrade','offline','low_storage','permission_denied','dark_mode','large_text'],'evidence_required':['device_model','os_version','build_sha256','screenshots','test_log']}
  write(out/'DEVICE_TEST_MATRIX.json',json.dumps(matrix,indent=2)+'\n'); files+=['DEVICE_TEST_MATRIX.json']
 elif n==31:
  write(out/'RELEASE_MANIFEST.json',json.dumps({'app':name,'version':app.get('version','1.0.0+1'),'artifacts':[],'signing_status':'NOT_CHECKED','upload_status':'NOT_PUBLISHED'},indent=2)+'\n'); files+=['RELEASE_MANIFEST.json']
 elif n==32:
  write(out/'PLAY_STORE_PREFLIGHT.md','# Play Store readiness preflight\n\n- [ ] App name, short and full description reviewed\n- [ ] Phone screenshots and feature graphic supplied\n- [ ] App icon supplied\n- [ ] Privacy policy URL verified\n- [ ] Data safety declaration matches actual behavior\n- [ ] Content rating and target audience completed\n- [ ] Permissions justified and minimized\n- [ ] Ads declaration and consent flows reviewed if applicable\n- [ ] Release tested; signing and upload evidence recorded\n\nThis checklist cannot guarantee Play policy approval.\n'); files+=['PLAY_STORE_PREFLIGHT.md']
 elif n==33:
  events={'events':[{'name':'app_open','parameters':['source']},{'name':'onboarding_complete','parameters':[]},{'name':'primary_action','parameters':['action_type']}],'privacy':['Collect only necessary analytics','Obtain consent where required','Provide opt-out where applicable','Do not send personal or sensitive data']}
  write(out/'ANALYTICS_PLAN.json',json.dumps(events,indent=2)+'\n'); files+=['ANALYTICS_PLAN.json']
 elif n==34:
  catalog=project/'templates'/'app_template_library.json'; data=jread(catalog,{'templates':[]}) or {'templates':[]}; data['templates'].append({'name':name,'source_project':str(project),'added_at':datetime.now(timezone.utc).isoformat(),'status':'LOCAL_CATALOG_ENTRY'})
  write(out/'TEMPLATE_LIBRARY_CATALOG.json',json.dumps(data,indent=2)+'\n'); files+=['TEMPLATE_LIBRARY_CATALOG.json']
 report={'milestone':n,'name':MILESTONES[n][0],'status':'GENERATED','project':str(project),'output':str(out),'files':files,'findings':findings,'timestamp':datetime.now(timezone.utc).isoformat()}
 write(out/'MILESTONE_REPORT.json',json.dumps(report,indent=2)+'\n'); return report

def main():
 p=argparse.ArgumentParser(description=__doc__); p.add_argument('--milestone',type=int,choices=MILESTONES,required=True); p.add_argument('--project',type=Path,default=ROOT); p.add_argument('--output',type=Path); a=p.parse_args(); print(json.dumps(run(a.milestone,a.project,a.output),indent=2))
if __name__=='__main__':main()
