"""`factory.py` command-line interface. Groups register themselves in GROUPS."""
from __future__ import annotations

import argparse
import getpass
import json
import sys
from pathlib import Path

from . import reports as R
from .approvals import ApprovalError, ApprovalRequired, ApprovalStore
from .audit import app_audit
from .context import DEFAULT_STATE_ROOT, RegistryError, resolve_app

GROUPS = {}  # name -> (help, add_arguments(parser), handler(args, app))


def group(name, help_text):
    def decorator(fn):
        GROUPS[name] = (help_text, fn)
        return fn
    return decorator


def _app(args):
    return resolve_app(args.app, args.project, args.registry, None, args.state_root)


def emit(args, report, save=True):
    path = None
    if save and not getattr(args, "no_save", False):
        path = R.write_report(args._app, report)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        R.print_summary(report, path)
    return 1 if report["status"] == R.FAIL else 0


# --- approvals ----------------------------------------------------------------

@group("approvals", "List, approve or deny human approval requests")
def _approvals(sub):
    sub.add_argument("action", choices=("list", "approve", "deny", "show"))
    sub.add_argument("request_id", nargs="?")
    sub.add_argument("--by", help="Your name (required to approve/deny)")
    sub.add_argument("--note", default="")
    sub.add_argument("--status")

    def handler(args, app):
        store = ApprovalStore.for_app(app)
        if args.action == "list":
            items = store.list(args.status)
            print(json.dumps(items, indent=2) if args.json else
                  "\n".join(f"{i['id']}  {i['status']:<9} {i['action']:<28} {i['reason']}" for i in items) or "No requests")
            return 0
        if not args.request_id:
            raise SystemExit("request_id is required")
        if args.action == "show":
            print(json.dumps(store.get(args.request_id), indent=2))
            return 0
        if args.action == "approve":
            item = store.get(args.request_id)
            print(json.dumps(item["payload_summary"], indent=2))
            if sys.stdin.isatty():
                answer = input(f"Approve '{item['description']}' for {app.app_id}? Type the request id to confirm: ")
                if answer.strip() != args.request_id:
                    print("Not approved.")
                    return 1
        item = store.decide(args.request_id, args.by, args.action == "approve", args.note)
        print(f"{item['id']} → {item['status']} by {item['decided_by']}")
        return 0
    return handler


@group("audit", "Show or verify the app's tamper-evident audit log")
def _audit(sub):
    sub.add_argument("action", choices=("show", "verify"))

    def handler(args, app):
        log = app_audit(app)
        if args.action == "verify":
            ok, bad = log.verify()
            print("Audit log intact" if ok else f"Audit log BROKEN at entry {bad}")
            return 0 if ok else 1
        for entry in log.entries()[-50:]:
            print(f"{entry['seq']:>4} {entry['at']} {entry['actor']:<14} {entry['event']} {json.dumps(entry['details'])}")
        return 0
    return handler


# --- milestone 41 -------------------------------------------------------------

@group("secrets", "M41 secure secrets: set, list, validate, scan, ci-template, rotation")
def _secrets(sub):
    sub.add_argument("action", choices=("set", "delete", "list", "validate", "scan", "ci-template", "rotation-guide"))
    sub.add_argument("--env", default="development", choices=("development", "staging", "production"))
    sub.add_argument("--name")

    def handler(args, app):
        from . import secrets_manager as S
        store = S.SecretStore(app)
        if args.action == "set":
            value = sys.stdin.readline().rstrip("\n") if not sys.stdin.isatty() else getpass.getpass(f"{args.name}: ")
            store.set(args.env, args.name, value)
            print(f"Stored {args.name} for {app.app_id}/{args.env} (value not shown)")
            return 0
        if args.action == "delete":
            print("Deleted" if store.delete(args.env, args.name) else "Not found")
            return 0
        if args.action == "list":
            meta = store.metadata(args.env)
            for name in store.names(args.env):
                print(f"{name}  rotated_at={meta.get(name, {}).get('rotated_at', '?')}")
            return 0
        if args.action == "validate":
            return emit(args, S.validate(app, args.env))
        if args.action == "scan":
            return emit(args, S.scan_exposure(app))
        if args.action == "ci-template":
            print(S.ci_template(app, args.env), end="")
            return 0
        print(S.ROTATION_GUIDANCE)
        return 0
    return handler


# --- milestone 42 -------------------------------------------------------------

@group("auth", "M42 authentication & authorization QA")
def _auth(sub):
    sub.add_argument("--execute", action="store_true", help="Run auth tests and live provider checks")
    sub.add_argument("--env", default="development")

    def handler(args, app):
        from .auth_qa import run_auth_qa
        return emit(args, run_auth_qa(app, args.execute, args.env))
    return handler


# --- milestone 43 -------------------------------------------------------------

@group("data", "M43 data, offline & backup readiness")
def _data(sub):
    sub.add_argument("action", nargs="?", default="check",
                     choices=("check", "device-backup", "device-restore", "offline-launch"))
    sub.add_argument("--execute", action="store_true")
    sub.add_argument("--update-snapshot", action="store_true")
    sub.add_argument("--package")
    sub.add_argument("--serial")
    sub.add_argument("--archive", type=Path)

    def handler(args, app):
        from . import data_readiness as D
        if args.action == "check":
            return emit(args, D.run_data_readiness(app, args.execute, args.update_snapshot))
        package = args.package or app.package_name
        if args.action == "device-backup":
            print(f"Backup written: {D.backup_device_data(app, package, args.serial)}")
        elif args.action == "device-restore":
            D.restore_device_data(app, package, args.archive, args.serial)
            print("Restored")
        else:
            print(json.dumps(D.simulate_offline_launch(app, package, args.serial), indent=2))
        return 0
    return handler


# --- milestone 44 -------------------------------------------------------------

@group("privacy", "M44 privacy inventory, Data Safety draft and sign-off")
def _privacy(sub):
    sub.add_argument("action", nargs="?", default="check", choices=("check", "signoff", "retention-template"))
    sub.add_argument("--execute", action="store_true", help="Check privacy policy URL reachability")

    def handler(args, app):
        from . import privacy as P
        report = P.run_privacy(app, args.execute)
        if args.action == "check":
            return emit(args, report)
        if args.action == "signoff":
            item = P.request_signoff(app, report)
            print(f"Sign-off request {item['id']} ({item['status']}). A human approves with:\n"
                  f"  python3 scripts/factory.py approvals approve {item['id']} --app {app.app_id} --by <name>")
            return 0
        print(P.retention_template(app, report), end="")
        return 0
    return handler


def build_parser():
    parser = argparse.ArgumentParser(prog="factory.py", description="MyAppFactory V7 command line")
    sub = parser.add_subparsers(dest="group", required=True)
    for name, (help_text, register) in GROUPS.items():
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--app", help="Registered app id (package name)")
        p.add_argument("--project", type=Path, help="Flutter project path (registered or ad hoc)")
        p.add_argument("--registry", type=Path)
        p.add_argument("--state-root", type=Path, default=DEFAULT_STATE_ROOT)
        p.add_argument("--json", action="store_true")
        p.add_argument("--no-save", action="store_true", help="Do not store the report")
        p.set_defaults(_handler=register(p))
    return parser


def main(argv=None):
    from . import extensions  # noqa: F401  (registers later-batch groups)
    args = build_parser().parse_args(argv)
    try:
        args._app = _app(args)
        return args._handler(args, args._app)
    except ApprovalRequired as exc:
        print(f"APPROVAL REQUIRED: {exc}", file=sys.stderr)
        return 3
    except (RegistryError, ApprovalError, PermissionError, FileExistsError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
