"""CLI group: milestones 45–49 (tests, devices, accessibility, performance, dependencies)."""
from __future__ import annotations

from pathlib import Path

from .cli import emit, group


@group("qa", "M45–49 tests, device matrix, accessibility harness, performance, dependency audit")
def _qa(sub):
    sub.add_argument("check", choices=("tests", "devices", "a11y", "perf", "deps"))
    sub.add_argument("--execute", action="store_true")
    sub.add_argument("--coverage", action="store_true")
    sub.add_argument("--device", help="adb serial")
    sub.add_argument("--apk", type=Path)
    sub.add_argument("--package")
    sub.add_argument("--allow-reinstall", action="store_true")
    sub.add_argument("--no-profiles", action="store_true")
    sub.add_argument("--build-mode", default="debug", choices=("debug", "profile", "release"))
    sub.add_argument("--osv", action="store_true", help="Query OSV.dev (sends package names/versions only)")
    sub.add_argument("--gradle", action="store_true")
    sub.add_argument("--root-widget")

    def handler(args, app):
        if args.check == "tests":
            from .qa_suite import run_tests
            return emit(args, run_tests(app, args.execute, args.coverage, args.device))
        if args.check == "deps":
            from .qa_suite import run_dependency_audit
            return emit(args, run_dependency_audit(app, args.execute, args.osv, args.gradle))
        from . import device_qa as D
        if args.check == "devices":
            return emit(args, D.run_device_matrix(app, args.apk, args.package, args.execute,
                                                  [args.device] if args.device else None,
                                                  args.allow_reinstall, not args.no_profiles))
        if args.check == "a11y":
            return emit(args, D.run_accessibility(app, args.execute, args.root_widget))
        return emit(args, D.measure_runtime(app, args.package, args.device, args.apk, build_mode=args.build_mode))
    return handler
