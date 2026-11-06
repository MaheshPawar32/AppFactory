#!/usr/bin/env python3
"""Create a validated app brief and generation plan from a concise wizard JSON."""
from __future__ import annotations
import argparse, json, re, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PACKAGE_RE=re.compile(r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9_]*)+$")
def slugify(value): return re.sub(r"[^a-z0-9]+","",value.lower()) or "myapp"
def parse_csv(value, default):
    vals=[x.strip() for x in (value or "").split(",") if x.strip()]
    return vals or list(default)
def make_brief(data):
    app=data.get("app",{})
    name=str(app.get("name","")).strip()
    if not name: raise ValueError("App name is required")
    slug=str(app.get("slug") or slugify(name))
    package=str(app.get("package_name") or f"com.dev.{slug}").strip()
    if not PACKAGE_RE.fullmatch(package): raise ValueError("Invalid package_name; use reverse-domain format such as com.dev.myapp")
    if not re.fullmatch(r"[a-z][a-z0-9_]*",slug): raise ValueError("slug must contain lowercase letters, digits and underscores, starting with a letter")
    platform=app.get("platform","android")
    if platform not in ("android","android_ios"): raise ValueError("platform must be android or android_ios")
    state=data.get("architecture",{})
    storage=data.get("storage",{})
    integrations=data.get("integrations",{})
    design=data.get("design",{})
    features=parse_csv(data.get("features",""),["onboarding","settings","offline_states"])
    locales=parse_csv(data.get("locales","en"),["en"])
    screens=parse_csv(data.get("screens","Home,Settings"),["Home","Settings"])
    backend=integrations.get("backend","none")
    if backend not in ("none","supabase","custom_api","firebase"): raise ValueError("backend must be none, supabase, custom_api or firebase")
    admob=bool(integrations.get("admob_enabled",False))
    firebase=bool(integrations.get("firebase_enabled",backend=="firebase"))
    return {
      "schema_version":1,"created_at_utc":datetime.now(timezone.utc).isoformat(),
      "app":{"name":name,"slug":slug,"package_name":package,"version":str(app.get("version","1.0.0+1")),
             "platform":platform,"project_type":"new","primary_goal":str(app.get("primary_goal","Describe the app's main purpose")).strip(),
             "target_users":parse_csv(data.get("target_users","general users"),["general users"]),
             "constraints":["Preserve existing work","Do not invent credentials","Android-first Flutter application"]},
      "architecture":{"state_management":state.get("state_management","Provider"),
                      "storage":storage.get("type","Hive"),"offline_first":bool(storage.get("offline_first",True))},
      "screens":[{"name":x,"purpose":f"Implement the {x} screen with loading, empty, error and accessibility states."} for x in screens],
      "features":features,"integrations":{"backend":backend,"firebase_enabled":firebase,
          "firebase_services":parse_csv(integrations.get("firebase_services",""),[]),
          "admob_enabled":admob,"admob_formats":parse_csv(integrations.get("admob_formats",""),[]) if admob else [],
          "credentials_provided":False,"setup_requires_user_action":bool(firebase or admob or backend!="none")},
      "design":{"style":design.get("style","modern_premium"),"locales":locales,
                "color_notes":str(design.get("color_notes",""))},
      "acceptance_criteria":["Core user journey works","Loading, empty, error and offline states are handled",
          "Preserve existing features and project conventions","Run formatter, analyzer and tests","Review privacy, permissions and release readiness"],
      "release":{"signing":"user_configured_only","publish_automatically":False}
    }

def create_plan(brief):
    return {"app_name":brief["app"]["name"],"package_name":brief["app"]["package_name"],
      "implementation_order":[
        {"step":1,"title":"Review starter and architecture","deliverable":"Confirm Flutter version, state management, folder structure and dependencies","approval_required":True},
        {"step":2,"title":"Design system and navigation","deliverable":"Theme, responsive navigation, routes and reusable UI components","approval_required":False},
        {"step":3,"title":"Core screens and models","deliverable":"Implement screens, domain models and validation","approval_required":False},
        {"step":4,"title":"Persistence and integrations","deliverable":"Implement offline storage and only the explicitly selected integrations","approval_required":True},
        {"step":5,"title":"Loading, error and accessibility states","deliverable":"Empty/error/offline states, semantics and adaptive layout","approval_required":False},
        {"step":6,"title":"Tests and QA","deliverable":"Unit/widget tests and optional device screenshot evidence","approval_required":False},
        {"step":7,"title":"Release preflight","deliverable":"Analyze, test, inspect permissions/assets and prepare release checklist","approval_required":True}],
      "notes":["This plan does not create app source or run Claude automatically.",
               "External service setup requires the user's own accounts and credentials.",
               "No signing keys are created and no app is published."]}

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,help="Wizard answers JSON")
    p.add_argument("--name",help="App name")
    p.add_argument("--package",help="Optional package ID; default com.dev.<slug>")
    p.add_argument("--goal",default="Describe the app's main purpose")
    p.add_argument("--features",default="onboarding,settings,offline_states")
    p.add_argument("--screens",default="Home,Settings")
    p.add_argument("--state-management",default="Provider",choices=("Provider","VelocityX","Riverpod","Bloc","GetX","None"))
    p.add_argument("--storage",default="Hive",choices=("Hive","SQLite","SharedPreferences","None"))
    p.add_argument("--backend",default="none",choices=("none","supabase","custom_api","firebase"))
    p.add_argument("--firebase",action="store_true")
    p.add_argument("--admob",action="store_true")
    p.add_argument("--locales",default="en")
    p.add_argument("--style",default="modern_premium")
    p.add_argument("--output",type=Path,default=ROOT/"generated_briefs")
    p.add_argument("--dry-run",action="store_true",help="Validate and print plan without writing files")
    a=p.parse_args(argv)
    try:
        if a.input:
            data=json.loads(a.input.read_text(encoding="utf-8"))
        else:
            if not a.name: p.error("provide --name or --input")
            data={"app":{"name":a.name,"package_name":a.package,"primary_goal":a.goal},
                  "features":a.features,"screens":a.screens,"architecture":{"state_management":a.state_management},
                  "storage":{"type":a.storage,"offline_first":True},
                  "integrations":{"backend":a.backend,"firebase_enabled":a.firebase,"admob_enabled":a.admob},
                  "locales":a.locales,"design":{"style":a.style}}
            if not a.package: data["app"].pop("package_name",None)
        brief=make_brief(data); plan=create_plan(brief)
        if a.dry_run:
            print(json.dumps({"valid":True,"brief":brief,"plan":plan},indent=2));return 0
        out=a.output.expanduser().resolve()/brief["app"]["slug"]
        out.mkdir(parents=True,exist_ok=False)
        (out/"APP_BRIEF.json").write_text(json.dumps(brief,indent=2)+"\n",encoding="utf-8")
        (out/"IMPLEMENTATION_PLAN.json").write_text(json.dumps(plan,indent=2)+"\n",encoding="utf-8")
        prompt=f"""# Claude Code implementation brief: {brief['app']['name']}

Use this validated app brief and implementation plan to build the Flutter application in the currently opened project. First inspect the existing project. Do not overwrite user work or change architecture without approval. Implement one plan step at a time, run formatting, analysis and tests, and report exact evidence. Ask before external integrations, credentials, permissions, signing or release actions. Never invent secrets or claim unrun checks passed.

Read `APP_BRIEF.json` and `IMPLEMENTATION_PLAN.json` in this directory. Start with step 1 and request approval for architecture before proceeding.
"""
        (out/"CLAUDE_CODE_START_PROMPT.md").write_text(prompt,encoding="utf-8")
        print(json.dumps({"status":"CREATED","output":str(out),"files":["APP_BRIEF.json","IMPLEMENTATION_PLAN.json","CLAUDE_CODE_START_PROMPT.md"]},indent=2))
        return 0
    except (OSError,json.JSONDecodeError,ValueError) as exc:
        print(json.dumps({"status":"INVALID","error":str(exc)},indent=2),file=sys.stderr);return 2
if __name__=="__main__": raise SystemExit(main())
