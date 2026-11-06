#!/usr/bin/env python3
"""Generate screen inventories, UI design prompts and image-reference workspaces."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

CORE = [
    ("splash", "Splash", "Brand introduction and app initialization"),
    ("onboarding", "Onboarding", "Explain the app value and request only necessary permissions"),
    ("home", "Home dashboard", "Primary daily-use overview and key actions"),
    ("settings", "Settings", "Preferences, privacy, theme and app information"),
]
DEFAULTS = {
    "fitness": [("activity", "Activity tracking", "Daily activity entry and progress"), ("history", "History", "Past activity and trends"), ("statistics", "Statistics", "Charts, goals and insights")],
    "productivity": [("tasks", "Task list", "Organize tasks and priorities"), ("task_detail", "Task detail", "View and edit a task"), ("calendar", "Calendar", "Upcoming schedule")],
    "content": [("feed", "Content feed", "Browse and discover content"), ("content_detail", "Content detail", "Read or view selected content"), ("saved", "Saved items", "Bookmarks and saved content")],
    "commerce": [("catalog", "Product catalogue", "Browse and search products"), ("product_detail", "Product detail", "Product information and options"), ("cart", "Cart", "Review selected items")],
    "community": [("feed", "Community feed", "Discover community posts"), ("detail", "Post detail", "View discussion and replies"), ("profile", "Profile", "Member profile and activity")],
    "api": [("list", "Data list", "Browse remote records"), ("detail", "Record detail", "Inspect a selected record"), ("connection_error", "Connection error", "Retry and offline recovery")],
    "utility": [("main_tool", "Main tool", "Perform the app's primary utility task"), ("result", "Result", "Show useful output and next actions"), ("history", "History", "Review previous actions")],
}
def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_") or "screen"
def generate(brief, output):
    app = brief.get("app", {})
    name = app.get("name", "My App")
    purpose = app.get("primary_goal", "Deliver the app's main user value")
    raw = brief.get("screens", [])
    if isinstance(raw, str):
        raw = [x.strip() for x in raw.split(",") if x.strip()]
    if isinstance(raw, dict):
        raw = raw.get("items", [])
    profile = str(brief.get("profile", brief.get("app_type", "utility"))).lower()
    rows = list(CORE)
    rows.extend(DEFAULTS.get(profile, []))
    seen = {r[0] for r in rows}
    for item in raw:
        label = item.get("name") if isinstance(item, dict) else str(item)
        if label and slug(label) not in seen:
            rows.append((slug(label), label, f"Support the {label.lower()} user journey"))
            seen.add(slug(label))
    screens = [{"id": sid, "name": title, "purpose": desc, "reference_file": f"ui_references/{sid}.png", "status": "REFERENCE_NEEDED"} for sid,title,desc in rows]
    output.mkdir(parents=True, exist_ok=True)
    refs = output / "ui_references"
    refs.mkdir(exist_ok=True)
    for s in screens:
        (refs / f"{s['id']}.README.md").write_text(f"# {s['name']} reference\n\nAdd the approved screenshot or design export as `{s['id']}.png`.\n", encoding="utf-8")
    (refs / "README.md").write_text("# UI reference images\n\nAdd one PNG/JPG per screen using the exact filename in `SCREEN_INVENTORY.json`. Number references REF-001 onward in `UI_REFERENCE_INDEX.md`. Do not use copyrighted screenshots as production assets; use them only as private design references where permitted.\n", encoding="utf-8")
    (output / "SCREEN_INVENTORY.json").write_text(json.dumps({"app": name, "screens": screens}, indent=2)+"\n", encoding="utf-8")
    lines = [f"# {name} — Screen inventory", "", f"**Purpose:** {purpose}", "", "| ID | Screen | Purpose | Reference |", "|---|---|---|---|"]
    lines += [f"| {s['id']} | {s['name']} | {s['purpose']} | `{s['reference_file']}` |" for s in screens]
    (output / "SCREEN_INVENTORY.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    design = f"""# UI design prompt pack — {name}

Act as a senior mobile product designer. Design a complete, production-ready Android UI for **{name}**.

Product purpose: {purpose}

## Design direction
- Premium, modern, clean, minimal and highly usable.
- Establish a cohesive design system: color tokens, typography scale, spacing, radius, elevation, icon style and reusable components.
- Use accessible contrast, touch targets, readable text and responsive layouts.
- Include loading, empty, error, offline, permission-denied and success states where relevant.
- Use realistic sample content; never invent backend capabilities or claim integrations are connected.

## Screen-by-screen deliverables
"""
    for i,s in enumerate(screens,1):
        design += f"\n{i}. **{s['name']}** (`{s['id']}`): {s['purpose']}. Define layout, hierarchy, components, interactions, validation and states.\n"
    design += """
## Output requirements
1. Provide one annotated screen design per screen, keeping one consistent design system.
2. Export each screen as a separate PNG at a consistent Android portrait frame (e.g. 1080×2400); do not combine unrelated screens into one collage.
3. Name files exactly as listed in `SCREEN_INVENTORY.json` and place them in `ui_references/`.
4. Also provide a design-system sheet and navigation-flow diagram.
5. Wait for approval of the design direction before implementing Flutter UI.
"""
    (output / "UI_DESIGN_PROMPTS.md").write_text(design, encoding="utf-8")
    (output / "UI_REFERENCE_INDEX.md").write_text("# UI reference index\n\n| Ref | Screen ID | File | Notes / approval |\n|---|---|---|---|\n" + "\n".join(f"| REF-{i:03d} | {s['id']} | `ui_references/{s['id']}.png` | Pending |" for i,s in enumerate(screens,1))+"\n", encoding="utf-8")
    (output / "CLAUDE_CODE_UI_INSTRUCTIONS.md").write_text(f"""# Claude Code UI implementation instructions — {name}

Before coding, read `APP_BRIEF.json`, `IMPLEMENTATION_PLAN.json`, `SCREEN_INVENTORY.md`, `SCREEN_INVENTORY.json`, `UI_DESIGN_PROMPTS.md`, `UI_REFERENCE_INDEX.md`, and inspect every image in `ui_references/`.

1. Confirm all planned screens and user journeys. Identify missing references; do not pretend a missing image exists.
2. Propose navigation map, design tokens, reusable component inventory and per-screen acceptance criteria.
3. Wait for human approval of the screen plan/design direction before large UI changes.
4. Implement screens incrementally, matching approved references while preserving app architecture and existing features.
5. Implement real interactions, validation, loading/empty/error/offline states and accessibility.
6. Add widget/unit tests for critical interactions. Capture runtime screenshots and compare them with approved references.
7. Update `UI_IMPLEMENTATION_STATUS.md` with DONE / IN PROGRESS / BLOCKED / NOT RUN and evidence paths.
8. Never generate fake functionality, credentials, external integrations, or claim tests/builds passed unless actually run.

Do not stop after the home screen. Complete every screen in `SCREEN_INVENTORY.json`.
""", encoding="utf-8")
    (output / "UI_IMPLEMENTATION_STATUS.md").write_text("# UI implementation status\n\n| Screen ID | Status | Evidence screenshot | Notes |\n|---|---|---|---|\n"+"\n".join(f"| {s['id']} | NOT STARTED | | |" for s in screens)+"\n", encoding="utf-8")
    return screens

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--brief",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    screens=generate(json.loads(a.brief.read_text(encoding="utf-8")),a.output)
    print(json.dumps({"status":"GENERATED","screen_count":len(screens),"output":str(a.output)},indent=2))
if __name__=="__main__": main()
