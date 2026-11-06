"""Milestones 46–48 — device compatibility, accessibility harness, runtime performance.

Device work only uses devices that are actually connected; profiles and API
levels that were not exercised are reported NOT RUN. Screen-profile runs use
`wm size` / `wm density` overrides and always reset them. The accessibility
harness is a generated widget test under the app's build/ directory (git-ignored,
not source) that measures Flutter accessibility guidelines, focus traversal and
layout overflow at several screen sizes and text scales.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from . import reports as R
from .context import AppContext, IsolationError
from .project import gradle_file, read_text
from .runner import run, run_binary

# Google Play target-API requirement changes yearly; verify before submission.
PLAY_TARGET_SDK = 36
PROFILES = {
    "compact_phone": ("720x1280", 320),
    "typical_phone": ("1080x2400", 420),
    "tablet": ("1600x2560", 320),
}
HARNESS_SIZES = {"compact": (320, 568), "phone": (411, 891), "tablet": (800, 1280)}
HARNESS_SCALES = (1.0, 1.5, 2.0)
DANGEROUS_PREFIX = "android.permission."


def _adb(serial):
    return ["adb", "-s", serial] if serial else ["adb"]


def _cwd(app):
    app.state_dir.mkdir(parents=True, exist_ok=True)
    return app.state_dir


def _belongs(app, package):
    if not app.package_name or not (package == app.package_name or package.startswith(app.package_name + ".")):
        raise IsolationError(f"{package} does not belong to {app.app_id}")


def sdk_levels(app) -> dict:
    gradle = gradle_file(app.root)
    text = read_text(gradle) if gradle else ""
    def find(key):
        match = re.search(rf"{key}\s*=?\s*(\d+)", text or "")
        return int(match.group(1)) if match else None
    return {"min_sdk": find("minSdk(?:Version)?"), "target_sdk": find("targetSdk(?:Version)?"),
            "compile_sdk": find("compileSdk(?:Version)?"), "gradle_file": str(gradle.relative_to(app.root)) if gradle else None}


def discover_devices(app) -> list[dict]:
    result = run(["adb", "devices", "-l"], _cwd(app), timeout=30)
    if not result.ok:
        return []
    devices = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 2 or parts[1] != "device":
            continue
        serial = parts[0]
        props = {}
        for key in ("ro.build.version.sdk", "ro.build.version.release", "ro.product.model", "ro.product.cpu.abi"):
            props[key] = run([*_adb(serial), "shell", "getprop", key], _cwd(app), timeout=15).stdout.strip()
        size = run([*_adb(serial), "shell", "wm", "size"], _cwd(app), timeout=15).stdout
        density = run([*_adb(serial), "shell", "wm", "density"], _cwd(app), timeout=15).stdout
        devices.append({"serial": serial, "emulator": serial.startswith("emulator-"),
                        "sdk": int(props["ro.build.version.sdk"]) if props["ro.build.version.sdk"].isdigit() else None,
                        "release": props["ro.build.version.release"], "model": props["ro.product.model"],
                        "abi": props["ro.product.cpu.abi"],
                        "size": (re.findall(r"(\d+x\d+)", size) or [None])[0],
                        "density": int((re.findall(r"(\d+)", density) or [0])[0])})
    return devices


def _installed(app, serial, package):
    return f"package:{package}" in run([*_adb(serial), "shell", "pm", "list", "packages", package],
                                      _cwd(app), timeout=30).stdout.split()


def _launch_and_check(app, serial, package, wait=4.0):
    adb = _adb(serial)
    run([*adb, "logcat", "-c", "-b", "crash"], _cwd(app), timeout=15)
    run([*adb, "shell", "am", "force-stop", package], _cwd(app), timeout=15)
    launch = run([*adb, "shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"],
                 _cwd(app), timeout=60)
    time.sleep(wait)
    alive = bool(run([*adb, "shell", "pidof", package], _cwd(app), timeout=15).stdout.strip())
    crash_log = run([*adb, "logcat", "-d", "-b", "crash"], _cwd(app), timeout=30).stdout
    return {"launched": launch.ok and "Events injected" in launch.stdout, "alive": alive,
            "crashed": package in crash_log, "crash_excerpt": crash_log[-1500:] if package in crash_log else ""}


def permission_state(app, serial, package) -> dict:
    dump = run([*_adb(serial), "shell", "dumpsys", "package", package], _cwd(app), timeout=30).stdout
    requested = sorted(set(re.findall(r"^\s+(android\.permission\.[A-Z_]+)\s*$", dump.split("install permissions:")[0]
                                      .split("requested permissions:")[-1], re.M)))
    runtime = dict(re.findall(r"(android\.permission\.[A-Z_]+): granted=(true|false)", dump))
    return {"requested": requested, "runtime": {k: v == "true" for k, v in runtime.items()}}


def screenshot(app, serial, target: Path) -> bool:
    code, data, _ = run_binary([*_adb(serial), "exec-out", "screencap", "-p"], _cwd(app), timeout=60)
    if code == 0 and data.startswith(b"\x89PNG"):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return True
    return False


def run_device_matrix(app: AppContext, apk=None, package=None, execute=False, serials=None,
                      allow_reinstall=False, profiles=True) -> dict:
    package = package or app.package_name
    levels = sdk_levels(app)
    checks = []
    min_sdk, target_sdk = levels["min_sdk"], levels["target_sdk"]
    checks.append(R.check("Minimum SDK", R.PASS if min_sdk else R.WARN,
                          f"minSdk {min_sdk}" if min_sdk else "minSdk not numeric in Gradle (flutter.minSdkVersion?)"))
    if target_sdk is None:
        checks.append(R.check("Target SDK vs Play requirement", R.WARN, "targetSdk not numeric in Gradle"))
    else:
        checks.append(R.check("Target SDK vs Play requirement", R.PASS if target_sdk >= PLAY_TARGET_SDK else R.FAIL,
                              f"targetSdk {target_sdk}; factory threshold {PLAY_TARGET_SDK} (verify current Play policy)"))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    matrix, artifacts = [], []
    if not execute:
        checks.append(R.check("Device runs", R.NOT_RUN, "Pass --execute with --apk"))
        return R.make_report(app, "device-qa", "Android device compatibility QA", checks, milestone=46,
                             data={"sdk": levels, "matrix": matrix})
    _belongs(app, package)
    if apk:
        apk = Path(apk).resolve()
        if not apk.is_file():
            raise FileNotFoundError(f"APK not found: {apk}")
        app.ensure_within(apk)
    devices = [d for d in discover_devices(app) if not serials or d["serial"] in serials]
    sdk_tools = run(["adb", "version"], _cwd(app), timeout=15)
    checks.append(R.check("Android SDK platform-tools", R.PASS if sdk_tools.ok else R.FAIL,
                          sdk_tools.stdout.splitlines()[0] if sdk_tools.ok and sdk_tools.stdout else "adb unavailable"))
    if not devices:
        checks.append(R.check("Devices", R.NOT_RUN, "No connected device or emulator"))
    for device in devices:
        serial = device["serial"]
        row = {**device, "install": None, "launch": None, "profiles": {}, "permissions": None}
        if min_sdk and device["sdk"] and device["sdk"] < min_sdk:
            row["install"] = "UNSUPPORTED"
            checks.append(R.check(f"{serial} (API {device['sdk']})", R.NOT_APPLICABLE, f"Below minSdk {min_sdk}"))
            matrix.append(row)
            continue
        present = _installed(app, serial, package)
        if apk and (not present or allow_reinstall):
            result = run([*_adb(serial), "install", "-r" if present else "-t", str(apk)], _cwd(app), timeout=300)
            row["install"] = "PASS" if result.ok and "Success" in result.stdout else f"FAIL: {result.stdout.strip()[-200:]}"
        elif present:
            row["install"] = "SKIPPED (already installed; pass --allow-reinstall to replace)"
        else:
            row["install"] = "NOT RUN (no --apk and package absent)"
        if _installed(app, serial, package):
            row["launch"] = _launch_and_check(app, serial, package)
            row["permissions"] = permission_state(app, serial, package)
            ok = row["launch"]["launched"] and row["launch"]["alive"] and not row["launch"]["crashed"]
            checks.append(R.check(f"{serial} API {device['sdk']} install+launch", R.PASS if ok else R.FAIL,
                                  f"install={row['install']}; launch={row['launch']['launched']}; alive={row['launch']['alive']}; "
                                  f"crash={row['launch']['crashed']}"))
            denied = [p for p, granted in row["permissions"]["runtime"].items() if not granted]
            checks.append(R.check(f"{serial} runtime permissions", R.PASS if not denied else R.MANUAL,
                                  f"{len(row['permissions']['runtime'])} runtime permission(s); not granted at launch: "
                                  f"{', '.join(denied) or 'none'} — verify the app's denial handling manually" if denied
                                  else f"{len(row['permissions']['runtime'])} runtime permission(s)"))
            if profiles:
                try:
                    for name, (size, density) in PROFILES.items():
                        run([*_adb(serial), "shell", "wm", "size", size], _cwd(app), timeout=15)
                        run([*_adb(serial), "shell", "wm", "density", str(density)], _cwd(app), timeout=15)
                        state = _launch_and_check(app, serial, package, wait=3.0)
                        shot = app.state_path("qa", "device", run_id, f"{serial}-{name}.png")
                        state["screenshot"] = str(shot) if screenshot(app, serial, shot) else None
                        if state["screenshot"]:
                            artifacts.append(state["screenshot"])
                        row["profiles"][name] = state
                        good = state["alive"] and not state["crashed"]
                        checks.append(R.check(f"{serial} profile {name} ({size}@{density})", R.PASS if good else R.FAIL,
                                              f"alive={state['alive']} crash={state['crashed']} screenshot={'yes' if state['screenshot'] else 'no'}"))
                finally:
                    run([*_adb(serial), "shell", "wm", "size", "reset"], _cwd(app), timeout=15)
                    run([*_adb(serial), "shell", "wm", "density", "reset"], _cwd(app), timeout=15)
        else:
            checks.append(R.check(f"{serial} install+launch", R.NOT_RUN, row["install"]))
        matrix.append(row)
    tested_apis = sorted({d["sdk"] for d in devices if d["sdk"]})
    if min_sdk and target_sdk:
        missing = [lvl for lvl in (min_sdk, target_sdk) if lvl not in tested_apis]
        checks.append(R.check("API level coverage", R.PASS if not missing else R.PARTIAL,
                              f"Tested: {tested_apis or 'none'}; not exercised: {missing or 'none'}"))
    return R.make_report(app, "device-qa", "Android device compatibility QA", checks, milestone=46,
                         data={"sdk": levels, "devices": devices, "matrix": matrix, "screenshots": artifacts},
                         limitations=["Screen profiles are wm size/density overrides on the available device(s), "
                                      "not distinct hardware.", "Physical-device behaviour is untested unless one is connected."],
                         manual=["Deny each runtime permission and confirm the app explains and recovers."])


# --- Milestone 47: accessibility harness --------------------------------------

HARNESS = r"""// GENERATED by MyAppFactory accessibility QA. Lives under build/ (git-ignored); safe to delete.
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:__PACKAGE__/main.dart' as app;

const sizes = <String, Size>{__SIZES__};
const scales = <double>[__SCALES__];

Future<Map<String, Object?>> check(WidgetTester tester, AccessibilityGuideline guideline) async {
  try {
    final result = await guideline.evaluate(tester);
    return {'passed': result.passed, 'reason': result.reason};
  } catch (error) {
    return {'passed': null, 'reason': 'evaluation error: $error'};
  }
}

// Real fonts: the default test font draws every glyph as a full em square, which
// grossly overstates text width and produces false overflow findings.
const fontDir = '__FONT_DIR__';

Future<void> loadFont(String family, List<String> files) async {
  final loader = FontLoader(family);
  var added = 0;
  for (final name in files) {
    final file = File('$fontDir/$name');
    if (file.existsSync()) {
      loader.addFont(file.readAsBytes().then((bytes) => ByteData.view(bytes.buffer)));
      added++;
    }
  }
  if (added > 0) await loader.load();
}

void main() {
  setUpAll(() async {
    await loadFont('Roboto', ['Roboto-Regular.ttf', 'Roboto-Medium.ttf', 'Roboto-Bold.ttf', 'Roboto-Black.ttf']);
    await loadFont('MaterialIcons', ['MaterialIcons-Regular.otf']);
    // ignore: avoid_print
    print('FACTORY_A11Y_FONTS ${File('$fontDir/Roboto-Regular.ttf').existsSync()}');
  });
  for (final entry in sizes.entries) {
    for (final scale in scales) {
      testWidgets('factory_a11y ${entry.key} x$scale', (tester) async {
        tester.view.devicePixelRatio = 2.0;
        tester.view.physicalSize = entry.value * 2.0;
        tester.platformDispatcher.textScaleFactorTestValue = scale;
        addTearDown(tester.view.reset);
        addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
        final semantics = tester.ensureSemantics();
        final layoutErrors = <String>[];
        final previous = FlutterError.onError;
        FlutterError.onError = (details) {
          final where = RegExp(r'(lib/[\w/]+\.dart:\d+)').firstMatch(details.toString())?.group(1);
          layoutErrors.add(details.exceptionAsString().split('\n').first + (where == null ? '' : ' at $where'));
        };
        try {
          await tester.pumpWidget(app.__ROOT__());
          await tester.pump(const Duration(milliseconds: 800));
        } finally {
          FlutterError.onError = previous;
        }
        final result = <String, Object?>{'size': entry.key, 'scale': scale, 'layout_errors': layoutErrors};
        if (scale == 1.0) {
          result['tap_target'] = await check(tester, androidTapTargetGuideline);
          result['labeled_tap_target'] = await check(tester, labeledTapTargetGuideline);
          result['text_contrast'] = await check(tester, textContrastGuideline);
          final stops = <int>{};
          for (var i = 0; i < 25; i++) {
            await tester.sendKeyEvent(LogicalKeyboardKey.tab);
            await tester.pump();
            final focus = FocusManager.instance.primaryFocus;
            if (focus != null && focus.context != null) stops.add(identityHashCode(focus));
          }
          result['focus_stops'] = stops.length;
        }
        semantics.dispose();
        // ignore: avoid_print
        print('FACTORY_A11Y ${jsonEncode(result)}');
      });
    }
  }
}
"""


def root_widget(app) -> str | None:
    text = read_text(app.root / "lib" / "main.dart") or ""
    match = re.search(r"runApp\(\s*(?:const\s+)?([A-Z]\w*)\s*\(\s*\)\s*\)", text)
    return match.group(1) if match else None


def material_font_dir() -> Path | None:
    import shutil
    flutter = shutil.which("flutter")
    if not flutter:
        return None
    path = Path(flutter).resolve().parents[1] / "bin" / "cache" / "artifacts" / "material_fonts"
    return path if (path / "Roboto-Regular.ttf").is_file() else None


def write_harness(app, root=None) -> Path:
    root = root or root_widget(app)
    if not root:
        raise ValueError("Could not find `runApp(RootWidget())` with a no-argument constructor in lib/main.dart")
    pubspec = read_text(app.root / "pubspec.yaml") or ""
    package = re.search(r"(?m)^name:\s*(\w+)", pubspec).group(1)
    sizes = ", ".join(f"'{k}': Size({w}, {h})" for k, (w, h) in HARNESS_SIZES.items())
    source = (HARNESS.replace("__PACKAGE__", package).replace("__ROOT__", root)
              .replace("__FONT_DIR__", str(material_font_dir() or ""))
              .replace("__SIZES__", sizes).replace("__SCALES__", ", ".join(str(s) for s in HARNESS_SCALES)))
    path = app.resolve("build/factory_a11y/factory_a11y_test.dart")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def evaluate_harness(results: list[dict]) -> list[dict]:
    checks = []
    base = [r for r in results if r["scale"] == 1.0]
    for key, name in (("tap_target", "Touch targets ≥48dp (androidTapTargetGuideline)"),
                      ("labeled_tap_target", "Tappable elements labelled (labeledTapTargetGuideline)"),
                      ("text_contrast", "Text contrast (textContrastGuideline)")):
        failures = [f"{r['size']}: {(r.get(key) or {}).get('reason', '')[:160]}" for r in base
                    if (r.get(key) or {}).get("passed") is False]
        errors = [r for r in base if (r.get(key) or {}).get("passed") is None]
        status = R.FAIL if failures else (R.NOT_RUN if errors and len(errors) == len(base) else R.PASS)
        checks.append(R.check(name, status, "; ".join(failures) or (f"Passed at {len(base) - len(errors)} size(s)")))
    for scale in HARNESS_SCALES:
        rows = [r for r in results if r["scale"] == scale]
        bad = [f"{r['size']}: {r['layout_errors'][0]}" for r in rows if r["layout_errors"]]
        label = "Layout at default text size" if scale == 1.0 else f"Text scaling x{scale}"
        checks.append(R.check(label, R.FAIL if bad else (R.PASS if rows else R.NOT_RUN),
                              "; ".join(bad[:3]) or f"No overflow at {len(rows)} screen size(s)"))
    stops = [r.get("focus_stops", 0) for r in base]
    checks.append(R.check("Keyboard focus traversal", R.PASS if stops and min(stops) > 0 else R.WARN,
                          f"Focus stops reached via Tab: {stops}"))
    return checks


def run_accessibility(app: AppContext, execute=False, root=None) -> dict:
    import sys
    scripts = str(Path(__file__).resolve().parents[1])
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import quality_qa_engine as QE
    static = QE.run_accessibility_qa(app.root, False, None)
    checks = [R.check("Static semantics heuristics", R.WARN if static.get("findings") else R.PASS,
                      f"{len(static.get('findings', []))} source finding(s)")]
    results, commands = [], []
    if execute:
        try:
            harness = write_harness(app, root)
        except ValueError as exc:
            checks.append(R.check("Accessibility harness", R.NOT_RUN, str(exc)))
        else:
            result = run(["flutter", "test", str(harness.relative_to(app.root)), "--reporter", "json"],
                         app.root, timeout=900)
            commands.append(result.to_dict(tail_lines=10))
            fonts_loaded = "FACTORY_A11Y_FONTS true" in result.stdout
            checks.append(R.check("Harness text metrics", R.PASS if fonts_loaded else R.WARN,
                                  "Real Roboto/Material Icons loaded" if fonts_loaded else
                                  "Test font used (wider than real text); overflow findings may be overstated"))
            for line in result.stdout.splitlines():
                if "FACTORY_A11Y " in line:
                    try:
                        message = json.loads(line).get("message", "")
                        results.append(json.loads(message.split("FACTORY_A11Y ", 1)[1]))
                    except (json.JSONDecodeError, IndexError):
                        continue
            if results:
                checks += evaluate_harness(results)
            else:
                checks.append(R.check("Accessibility harness", R.FAIL,
                                      "Harness produced no results: " + (result.stderr or result.stdout)[-300:]))
    else:
        checks.append(R.check("Accessibility harness", R.NOT_RUN, "Pass --execute to run the generated widget harness"))
    checks.append(R.check("Screen reader (TalkBack) walkthrough", R.MANUAL, "Follow the checklist in the report"))
    return R.make_report(app, "accessibility", "Accessibility & UX QA", checks, milestone=47,
                         data={"static": static.get("findings", []), "harness_results": results},
                         commands=commands,
                         limitations=["The harness pumps the root widget only; screens behind navigation need "
                                      "app-specific widget tests.", "Guidelines are Flutter's automated checks, "
                                      "not a WCAG conformance audit."],
                         manual=["TalkBack: every control announces a meaningful label and role.",
                                 "TalkBack: reading order follows the visual order.",
                                 "Focus is moved to dialogs and returned when they close.",
                                 "No information is conveyed by colour alone.",
                                 "Animations respect 'Remove animations'."])


# --- Milestone 48: runtime performance -----------------------------------------

THRESHOLDS = {"apk_growth_pct": 10.0, "janky_pct_increase": 5.0, "pss_growth_pct": 20.0, "startup_growth_pct": 25.0}


def parse_gfxinfo(text: str) -> dict:
    def num(pattern, cast=float):
        match = re.search(pattern, text)
        return cast(match.group(1)) if match else None
    return {"total_frames": num(r"Total frames rendered:\s*(\d+)", int),
            "janky_frames": num(r"Janky frames:\s*(\d+)", int),
            "janky_pct": num(r"Janky frames:\s*\d+\s*\(([\d.]+)%\)"),
            "p50_ms": num(r"50th percentile:\s*(\d+)ms"), "p90_ms": num(r"90th percentile:\s*(\d+)ms"),
            "p99_ms": num(r"99th percentile:\s*(\d+)ms")}


def parse_meminfo(text: str) -> int | None:
    match = re.search(r"TOTAL PSS:\s*(\d+)", text) or re.search(r"^\s*TOTAL\s+(\d+)", text, re.M)
    return int(match.group(1)) if match else None


def _perf_history(app):
    return app.state_path("qa", "perf_history.jsonl")


def compare(previous: dict | None, current: dict, thresholds=THRESHOLDS) -> list[str]:
    if not previous:
        return []
    warnings = []
    def growth(key):
        a, b = previous.get(key), current.get(key)
        return (b - a) / a * 100 if a and b is not None else None
    for key, limit, label in (("apk_bytes", "apk_growth_pct", "APK size"), ("pss_kb", "pss_growth_pct", "Memory (PSS)"),
                              ("startup_ms", "startup_growth_pct", "Startup time")):
        value = growth(key)
        if value is not None and value > thresholds[limit]:
            warnings.append(f"{label} +{value:.1f}% (threshold {thresholds[limit]}%)")
    a, b = previous.get("janky_pct"), current.get("janky_pct")
    if a is not None and b is not None and b - a > thresholds["janky_pct_increase"]:
        warnings.append(f"Janky frames {a}%→{b}%")
    return warnings


def measure_runtime(app: AppContext, package=None, serial=None, apk=None, seconds=8.0, build_mode="debug") -> dict:
    package = package or app.package_name
    _belongs(app, package)
    adb = _adb(serial)
    cwd = _cwd(app)
    run([*adb, "shell", "am", "force-stop", package], cwd, timeout=15)
    run([*adb, "shell", "dumpsys", "gfxinfo", package, "reset"], cwd, timeout=15)
    run([*adb, "logcat", "-c", "-b", "crash"], cwd, timeout=15)
    resolve = run([*adb, "shell", "cmd", "package", "resolve-activity", "--brief", package], cwd, timeout=15)
    component = (resolve.stdout.strip().splitlines() or [""])[-1]
    start = run([*adb, "shell", "am", "start", "-W", "-n", component], cwd, timeout=60) if "/" in component else None
    startup = None
    if start and start.ok:
        match = re.search(r"TotalTime:\s*(\d+)", start.stdout)
        startup = int(match.group(1)) if match else None
    time.sleep(seconds)
    gfx = parse_gfxinfo(run([*adb, "shell", "dumpsys", "gfxinfo", package], cwd, timeout=30).stdout)
    pss = parse_meminfo(run([*adb, "shell", "dumpsys", "meminfo", package], cwd, timeout=30).stdout)
    crash = run([*adb, "logcat", "-d", "-b", "crash"], cwd, timeout=30).stdout
    apk_bytes = Path(apk).stat().st_size if apk and Path(apk).is_file() else None
    current = {"at": datetime.now(timezone.utc).isoformat(), "build_mode": build_mode, "package": package,
               "startup_ms": startup, "pss_kb": pss, "apk_bytes": apk_bytes, "crashed": package in crash, **gfx}
    history_path = _perf_history(app)
    previous = None
    if history_path.is_file():
        same_mode = [json.loads(l) for l in history_path.read_text(encoding="utf-8").splitlines()
                     if l.strip() and json.loads(l).get("build_mode") == build_mode]
        previous = same_mode[-1] if same_mode else None
    regressions = compare(previous, current)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(current) + "\n")
    checks = [
        R.check("Cold start (am start -W)", R.PASS if startup is not None else R.NOT_RUN,
                f"{startup} ms ({build_mode} build)" if startup is not None else "Launch activity not resolved"),
        R.check("Frame rendering (gfxinfo)", R.PASS if gfx["total_frames"] else R.NOT_RUN,
                f"{gfx['total_frames']} frames, janky {gfx['janky_pct']}%, p90 {gfx['p90_ms']} ms"
                if gfx["total_frames"] else "No frames recorded"),
        R.check("Memory (PSS)", R.PASS if pss else R.NOT_RUN, f"{pss} KB" if pss else "meminfo unavailable"),
        R.check("Crash buffer", R.FAIL if current["crashed"] else R.PASS,
                "Crash recorded for this package" if current["crashed"] else "No crash"),
        R.check("Build-to-build comparison", R.WARN if regressions else (R.PASS if previous else R.NOT_RUN),
                "; ".join(regressions) or ("Within thresholds" if previous else "First measurement for this build mode")),
    ]
    return R.make_report(app, "performance", "Performance & stability", checks, milestone=48,
                         data={"current": current, "previous": previous, "regressions": regressions,
                               "thresholds": THRESHOLDS, "crash_excerpt": crash[-1500:] if current["crashed"] else ""},
                         limitations=[f"Measured on a {build_mode} build; debug builds are much slower than release.",
                                      "Single emulator run; repeat on physical devices for decisions."])
