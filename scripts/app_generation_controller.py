#!/usr/bin/env python3
"""Resumable, approval-gated task controller for Claude-assisted Flutter app generation.

The controller plans and tracks work; it does not call Claude, modify app source,
run shell commands from a brief, or claim tasks are complete without an explicit
completion action. Generated task prompts are intended to be pasted into Claude Code.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, json, re, sys

SCHEMA_VERSION = 1
STATUSES = {"PENDING", "IN_PROGRESS", "BLOCKED", "COMPLETED", "SKIPPED"}
APPROVAL_TASKS = {"architecture_review", "integration_setup", "release_preparation"}

def now():
    return datetime.now(timezone.utc).isoformat()

def slugify(value):
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "new_app"

def load_json(path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)

def task(task_id, title, objective, deliverables, acceptance, approval=False):
    return {"id": task_id, "title": title, "objective": objective,
            "deliverables": deliverables, "acceptance_criteria": acceptance,
            "status": "PENDING", "approval_required": approval,
            "approved": not approval, "approval_note": "",
            "started_at": None, "completed_at": None, "evidence": []}

def build_tasks(brief):
    app = brief.get("app", {})
    name = app.get("name", "New Flutter App")
    screens = brief.get("screens", [])
    integrations = brief.get("integrations", [])
    return [
        task("brief_review", "Review app brief and constraints",
             f"Review requirements for {name}; identify ambiguity, risks and out-of-scope items before coding.",
             ["requirements_summary.md", "open_questions.md"],
             ["Core user problem and target users are stated", "Constraints and non-goals are recorded", "No credentials or sensitive data are embedded"]),
        task("screen_plan", "Plan screens and navigation",
             "Turn the brief and reference images into a screen inventory, navigation map, reusable component list and state/empty/error/loading states.",
             ["SCREEN_INVENTORY.md", "NAVIGATION_MAP.md", "COMPONENT_INVENTORY.md"],
             ["Every requested screen is mapped", "Primary journeys have start/end states", "Loading, empty, error and offline states are considered"]),
        task("architecture_review", "Propose architecture and data model",
             "Choose architecture, state management, storage, routing and data models consistent with project constraints. Explain trade-offs before implementation.",
             ["ARCHITECTURE.md", "DATA_MODEL.md"],
             ["Existing project conventions are preserved", "Data ownership and migrations are addressed", "No unnecessary dependencies are added"], True),
        task("design_system", "Align UI with design system",
             "Inspect existing design system and references; define tokens, typography, spacing, component variants, responsive behavior and motion/loading rules.",
             ["DESIGN_IMPLEMENTATION_PLAN.md"],
             ["Existing design system is reused where suitable", "Accessibility and text scaling are considered", "No reference image is copied as a flattened screen"]),
        task("implementation", "Implement app incrementally",
             "Implement the approved plan in small, reviewable slices. Preserve existing features and avoid unrelated refactors.",
             ["Working Flutter source", "Updated implementation progress"],
             ["Each task is tied to acceptance criteria", "No placeholder-only core journey remains", "Errors and offline states are handled"]),
        task("integration_setup", "Configure optional integrations",
             "Integrate only explicitly selected services. Ask for user-provided setup where needed; never invent keys, account IDs or credentials.",
             ["Integration status report", "Setup instructions for missing user-owned configuration"],
             ["Unselected integrations remain absent", "Secrets are not committed", "Unavailable configuration is reported as BLOCKED"], True),
        task("quality_tests", "Add and run quality checks",
             "Add unit/widget/integration tests for critical journeys and run formatter, analyzer and tests in the configured environment.",
             ["Test coverage map", "Actual command outputs or logs", "Known issues list"],
             ["Results reflect real command exit codes", "Critical journeys have tests", "Unrun checks are labeled NOT RUN"]),
        task("visual_qa", "Review visual quality and accessibility",
             "Run app on available target devices, inspect screenshots and check overflow, contrast, touch targets, font scaling and loading transitions.",
             ["Visual QA report", "Screenshots or explicit NOT RUN reasons"],
             ["Screens/states are reviewed at relevant sizes", "Visual issues have severity and retest status", "No claim of screenshot review without evidence"]),
        task("release_preparation", "Prepare release evidence",
             "Check version, package ID, Android permissions, privacy disclosures, asset licenses, signing setup and release notes. Do not publish.",
             ["Release checklist", "Release verification report"],
             ["Build artifact exists and is identified when built", "Signing is verified without exposing private keys", "Store compliance review is explicit"], True),
    ]

def initialize(workspace, brief_path):
    brief_path = brief_path.resolve()
    brief = load_json(brief_path)
    if not isinstance(brief, dict) or not isinstance(brief.get("app"), dict):
        raise ValueError("Brief must be a JSON object containing an 'app' object.")
    name = str(brief["app"].get("name", "")).strip()
    if not name:
        raise ValueError("brief.app.name is required.")
    if workspace.exists():
        raise FileExistsError(f"Workspace already exists; refusing to overwrite: {workspace}")
    workspace.mkdir(parents=True)
    (workspace / "evidence").mkdir()
    (workspace / "prompts").mkdir()
    state = {
        "schema_version": SCHEMA_VERSION, "app_name": name,
        "workspace": str(workspace.resolve()), "brief_path": str(brief_path),
        "created_at": now(), "updated_at": now(), "current_task_id": None,
        "paused": False, "tasks": build_tasks(brief),
        "history": [{"event": "initialized", "at": now(), "detail": "Task plan created; no app source generated."}],
        "safety": {"preserve_existing_work": True, "no_auto_publish": True,
                   "no_invented_credentials": True, "approval_gates_required": True}
    }
    (workspace / "brief.json").write_text(json.dumps(brief, indent=2), encoding="utf-8")
    save_state(workspace, state)
    return state

def save_state(workspace, state):
    state["updated_at"] = now()
    path = workspace / "workflow_state.json"
    temp = workspace / "workflow_state.json.tmp"
    temp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temp.replace(path)

def load_state(workspace):
    path = workspace / "workflow_state.json"
    if not path.is_file():
        raise FileNotFoundError(f"No workflow state at {path}; initialize a workspace first.")
    state = load_json(path)
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported workflow state schema; back up the workspace before migration.")
    return state

def next_task(state):
    for item in state["tasks"]:
        if item["status"] in ("PENDING", "IN_PROGRESS", "BLOCKED"):
            return item
    return None

def task_prompt(state, item):
    return f"""# Claude Code task: {item['title']}

App: {state['app_name']}
Task ID: {item['id']}
Task objective: {item['objective']}

## Required deliverables
{chr(10).join('- ' + x for x in item['deliverables'])}

## Acceptance criteria
{chr(10).join('- [ ] ' + x for x in item['acceptance_criteria'])}

## Working rules
- Read `brief.json` and `workflow_state.json` before making changes.
- Inspect the existing project before editing. Preserve user changes and existing features.
- Work only on this task; do not silently expand scope or perform unrelated refactors.
- Ask before destructive changes, overwriting files, adding paid services, connecting accounts, signing, publishing, or changing package identity.
- Never invent credentials or claim a command/test/build succeeded unless you actually ran it and observed the result.
- Update the task deliverables and evidence honestly. Mark unavailable checks `NOT RUN` and blockers `BLOCKED`.
- Do not modify `workflow_state.json` by guessing status. The user should record status with the controller commands.
"""

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create a new workflow workspace from a JSON app brief")
    init.add_argument("--brief", type=Path, required=True)
    init.add_argument("--workspace", type=Path, required=True)
    status = sub.add_parser("status", help="Show saved task status")
    status.add_argument("--workspace", type=Path, required=True)
    nxt = sub.add_parser("next", help="Generate a prompt for the next resumable task")
    nxt.add_argument("--workspace", type=Path, required=True)
    nxt.add_argument("--output", type=Path, help="Write prompt to this file instead of stdout")
    start = sub.add_parser("start", help="Mark a task in progress")
    start.add_argument("--workspace", type=Path, required=True)
    start.add_argument("--task", required=True)
    complete = sub.add_parser("complete", help="Record completion with evidence; approval-gated tasks need approval first")
    complete.add_argument("--workspace", type=Path, required=True)
    complete.add_argument("--task", required=True)
    complete.add_argument("--evidence", action="append", default=[], help="Evidence path or command/result note; repeatable")
    block = sub.add_parser("block", help="Record a blocker")
    block.add_argument("--workspace", type=Path, required=True)
    block.add_argument("--task", required=True)
    block.add_argument("--reason", required=True)
    approve = sub.add_parser("approve", help="Explicitly approve a gated task")
    approve.add_argument("--workspace", type=Path, required=True)
    approve.add_argument("--task", required=True)
    approve.add_argument("--note", required=True)
    pause = sub.add_parser("pause", help="Pause/resume workflow")
    pause.add_argument("--workspace", type=Path, required=True)
    pause.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    try:
        workspace = args.workspace.expanduser().resolve()
        if args.command == "init":
            state = initialize(workspace, args.brief.expanduser())
            print(f"Initialized workflow for {state['app_name']}: {workspace}")
            print(f"Tasks: {len(state['tasks'])}; no app code was generated.")
            return 0
        state = load_state(workspace)
        if args.command == "status":
            print(json.dumps({"app_name": state["app_name"], "paused": state["paused"],
                              "current_task_id": state["current_task_id"],
                              "tasks": [{"id": t["id"], "title": t["title"], "status": t["status"],
                                         "approval_required": t["approval_required"], "approved": t["approved"]}
                                        for t in state["tasks"]]}, indent=2))
            return 0
        if args.command == "pause":
            state["paused"] = not args.resume
            state["history"].append({"event": "resumed" if args.resume else "paused", "at": now()})
            save_state(workspace, state)
            print("Workflow " + ("resumed." if args.resume else "paused."))
            return 0
        task_id = args.task if args.command in ("start", "complete", "block", "approve") else None
        item = next((t for t in state["tasks"] if t["id"] == task_id), None) if task_id else None
        if args.command == "next":
            if state["paused"]:
                print("Workflow is paused. Use the pause command with --resume.")
                return 2
            item = next_task(state)
            if not item:
                print("All planned tasks are terminal (completed/skipped).")
                return 0
            if item["approval_required"] and not item["approved"]:
                print(f"Approval required before proceeding: {item['id']} — {item['title']}")
                print("Use approve only after a human reviews the plan and records a meaningful note.")
                return 3
            prompt = task_prompt(state, item)
            if args.output:
                out = args.output.expanduser().resolve()
                out.parent.mkdir(parents=True, exist_ok=True)
                if out.exists():
                    raise FileExistsError(f"Refusing to overwrite prompt: {out}")
                out.write_text(prompt, encoding="utf-8")
                print(f"Prompt written: {out}")
            else:
                print(prompt)
            return 0
        if not item:
            raise ValueError(f"Unknown task id: {task_id}")
        if args.command == "start":
            if state["paused"]:
                raise ValueError("Workflow is paused; resume it before starting a task.")
            if item["approval_required"] and not item["approved"]:
                raise ValueError(f"Task {task_id} requires explicit approval before starting.")
            item["status"] = "IN_PROGRESS"
            item["started_at"] = item["started_at"] or now()
            state["current_task_id"] = task_id
            state["history"].append({"event": "task_started", "task_id": task_id, "at": now()})
        elif args.command == "approve":
            if not item["approval_required"]:
                raise ValueError(f"Task {task_id} does not require an approval gate.")
            item["approved"] = True
            item["approval_note"] = args.note
            state["history"].append({"event": "task_approved", "task_id": task_id, "note": args.note, "at": now()})
        elif args.command == "block":
            item["status"] = "BLOCKED"
            item["blocker"] = args.reason
            state["history"].append({"event": "task_blocked", "task_id": task_id, "reason": args.reason, "at": now()})
        elif args.command == "complete":
            if item["approval_required"] and not item["approved"]:
                raise ValueError(f"Task {task_id} requires explicit approval before completion.")
            if not args.evidence:
                raise ValueError("At least one --evidence entry is required to record completion.")
            item["status"] = "COMPLETED"
            item["completed_at"] = now()
            item["evidence"].extend(args.evidence)
            item.pop("blocker", None)
            state["history"].append({"event": "task_completed", "task_id": task_id,
                                     "evidence": args.evidence, "at": now()})
            if state.get("current_task_id") == task_id:
                state["current_task_id"] = None
        save_state(workspace, state)
        print(f"{args.command} recorded for {task_id}.")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
