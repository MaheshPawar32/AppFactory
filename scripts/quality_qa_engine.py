#!/usr/bin/env python3
"""Project-scoped Flutter testing, Android QA, accessibility, performance and dependency evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

TEST_SUFFIX = "_test.dart"
INTERACTIVE = re.compile(r"\b(?:IconButton|TextButton|ElevatedButton|OutlinedButton|InkWell|GestureDetector)\b")
SEMANTIC_LABEL = re.compile(r"\b(?:tooltip|semanticLabel|Semantics|label)\s*:")
SECRET_ENV = re.compile(r"(?:TOKEN|PASSWORD|SECRET|API_KEY|PRIVATE_KEY)", re.IGNORECASE)
SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b((?:access[_-]?token|password|secret|api[_-]?key)\s*[=:]\s*)"
    r"([^\s,;]+)"
)


def _status(items, empty="NOT RUN"):
    statuses = [item.get("status", "NOT RUN") for item in items]
    if "FAIL" in statuses:
        return "FAIL"
    if "BLOCKED" in statuses:
        return "PARTIAL"
    if statuses and all(status == "PASS" for status in statuses):
        return "PASS"
    if not statuses or all(status == "NOT RUN" for status in statuses):
        return empty
    return "PARTIAL"


def validate_project(project):
    root = Path(project).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f"Flutter project directory does not exist: {root}")
    if not (root / "pubspec.yaml").is_file():
        raise ValueError(f"Flutter project manifest not found: {root / 'pubspec.yaml'}")
    return root


def _scan_test_files(project):
    result = {}
    test_root = project / "test"
    if test_root.is_dir():
        for path in sorted(test_root.rglob(f"*{TEST_SUFFIX}")):
            relative = path.relative_to(test_root)
            parts = {part.lower() for part in relative.parts[:-1]}
            stem = path.stem.lower()
            if "api" in parts or "api" in stem:
                suite = "api"
            elif "offline" in parts or "offline" in stem:
                suite = "offline"
            elif "regression" in parts or "regression" in stem:
                suite = "regression"
            else:
                try:
                    is_widget = "testWidgets(" in path.read_text(encoding="utf-8")
                except (OSError, UnicodeError):
                    is_widget = False
                suite = "widget" if is_widget else "unit"
            result.setdefault(suite, []).append(path)
    integration_root = project / "integration_test"
    integration = sorted(integration_root.rglob(f"*{TEST_SUFFIX}")) if integration_root.is_dir() else []
    if integration:
        result["integration"] = integration
    return result


def discover_test_plan(project, device=None):
    discovered = _scan_test_files(project)
    suites = []
    for name in ("unit", "widget", "api", "offline", "regression", "integration"):
        files = discovered.get(name, [])
        if not files:
            suites.append({"suite": name, "status": "NOT RUN", "reason": "No matching test files discovered"})
            continue
        if name == "integration" and not device:
            suites.append({
                "suite": name, "status": "NOT RUN",
                "reason": "Integration tests require an available Android device/emulator",
                "files": [str(path) for path in files],
            })
            continue
        relative = [str(path.relative_to(project)) for path in files]
        command = ["flutter", "test"]
        if name == "integration":
            command = ["flutter", "test", "integration_test", "-d", device]
        else:
            command.extend(relative)
        suites.append({"suite": name, "status": "PLANNED", "files": relative, "command": command})
    return suites


def _redact(text):
    result = str(text or "")
    for key, value in os.environ.items():
        if SECRET_ENV.search(key) and value and len(value) >= 4:
            result = result.replace(value, "[REDACTED]")
    return SECRET_ASSIGNMENT.sub(r"\1[REDACTED]", result)


def _run_command(command, cwd, timeout, log_path=None, include_stdout=False):
    started = time.monotonic()
    try:
        proc = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False,
        )
        stdout, stderr = _redact(proc.stdout), _redact(proc.stderr)
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(
                f"$ {command!r}\n\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}\n",
                encoding="utf-8",
            )
        result = {
            "status": "PASS" if proc.returncode == 0 else "FAIL",
            "command": command,
            "exit_code": proc.returncode,
            "duration_seconds": round(time.monotonic() - started, 2),
            "stdout_tail": stdout.splitlines()[-30:],
            "stderr_tail": stderr.splitlines()[-30:],
            "log_path": str(log_path) if log_path else None,
        }
        if include_stdout:
            result["_stdout"] = stdout
        return result
    except subprocess.TimeoutExpired as exc:
        stdout = _redact(exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout)
        stderr = _redact(exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr)
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(
                f"$ {command!r}\n\nTIMEOUT after {timeout} seconds\n"
                f"--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}\n",
                encoding="utf-8",
            )
        return {
            "status": "FAIL", "command": command, "exit_code": None,
            "duration_seconds": round(time.monotonic() - started, 2),
            "stdout_tail": stdout.splitlines()[-30:], "stderr_tail": stderr.splitlines()[-30:],
            "error": f"Command timed out after {timeout} seconds",
            "log_path": str(log_path) if log_path else None,
        }
    except OSError as exc:
        return {
            "status": "BLOCKED", "command": command, "exit_code": None,
            "duration_seconds": round(time.monotonic() - started, 2),
            "error": f"Unable to execute command: {exc}",
        }


def run_test_engine(project, execute=False, output_dir=None, device=None):
    project = validate_project(project)
    suites = discover_test_plan(project, device)
    result = {
        "milestone": 45, "name": "Automated Testing Engine",
        "project": str(project), "mode": "EXECUTE" if execute else "DRY RUN",
        "test_suites": [], "missing_test_categories": [],
        "note": "Absent test categories remain NOT RUN; missing tests are never treated as passed.",
    }
    if not execute:
        for suite in suites:
            item = dict(suite)
            if item["status"] == "PLANNED":
                item["status"] = "DRY RUN"
            result["test_suites"].append(item)
    else:
        if not shutil.which("flutter"):
            result["test_suites"] = [
                {**suite, "status": "BLOCKED", "reason": "Flutter executable not found"}
                if suite["status"] == "PLANNED" else suite for suite in suites
            ]
        else:
            for suite in suites:
                if suite["status"] != "PLANNED":
                    result["test_suites"].append(suite)
                    result["missing_test_categories"].append(suite["suite"])
                    continue
                safe_name = re.sub(r"[^a-z0-9_-]", "_", suite["suite"].lower())
                log = Path(output_dir) / f"{safe_name}.log" if output_dir else None
                item = _run_command(suite["command"], project, 900, log)
                item.update({"suite": suite["suite"], "files": suite["files"]})
                result["test_suites"].append(item)
        result["missing_test_categories"] = [
            item["suite"] for item in result["test_suites"] if item["status"] == "NOT RUN"
        ]
    result["overall_status"] = _status(result["test_suites"], empty="PARTIAL")
    if result["overall_status"] == "PASS" and result["missing_test_categories"]:
        result["overall_status"] = "PARTIAL"
    result["summary"] = {
        "discovered_files": sum(len(item.get("files", [])) for item in result["test_suites"]),
        "executed_suites": sum(item.get("status") == "PASS" or item.get("status") == "FAIL"
                               for item in result["test_suites"]),
        "missing_categories": result["missing_test_categories"],
    }
    return result


def _android_gradle(project):
    candidates = [
        project / "android" / "app" / "build.gradle.kts",
        project / "android" / "app" / "build.gradle",
    ]
    path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if not path:
        return None, {"status": "NOT RUN", "reason": "Android app Gradle file not found"}
    text = path.read_text(encoding="utf-8", errors="replace")
    values = {}
    for key, patterns in {
        "min_sdk": (r"\bminSdk\s*=\s*(\d+)", r"\bminSdk\s+(\d+)"),
        "target_sdk": (r"\btargetSdk\s*=\s*(\d+)", r"\btargetSdk\s+(\d+)"),
        "compile_sdk": (r"\bcompileSdk\s*=\s*(\d+)", r"\bcompileSdk\s+(\d+)"),
    }.items():
        match = next((re.search(pattern, text) for pattern in patterns if re.search(pattern, text)), None)
        values[key] = int(match.group(1)) if match else None
    app_id = re.search(r"\bapplicationId\s*(?:=\s*)?[\"']([^\"']+)[\"']", text)
    values["application_id"] = app_id.group(1) if app_id else None
    values["gradle_file"] = str(path)
    if values["min_sdk"] is None or values["target_sdk"] is None:
        return values, {"status": "PARTIAL", "reason": "minSdk/targetSdk are dynamic or unresolved in Gradle"}
    if values["target_sdk"] < values["min_sdk"]:
        return values, {"status": "FAIL", "reason": "targetSdk is lower than minSdk"}
    return values, {"status": "PASS", "reason": "Numeric minimum and target Android SDK values are consistent"}


def _flutter_android_devices():
    flutter = shutil.which("flutter")
    if not flutter:
        return [], {"status": "NOT RUN", "reason": "Flutter executable not found"}
    try:
        proc = subprocess.run(
            [flutter, "devices", "--machine"], capture_output=True, text=True, timeout=30, check=False,
        )
        if proc.returncode:
            return [], {"status": "FAIL", "error": _redact(proc.stderr[-2000:])}
        devices = json.loads(proc.stdout)
        android = [
            {"id": device.get("id"), "name": device.get("name"),
             "target_platform": device.get("targetPlatform"), "emulator": device.get("emulator", False),
             "sdk": device.get("sdk")}
            for device in devices if str(device.get("targetPlatform", "")).startswith("android")
        ]
        return android, {"status": "PASS" if android else "NOT RUN",
                         "reason": "Android devices discovered" if android else "No Android device or emulator connected"}
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return [], {"status": "FAIL", "error": str(exc)}


def _sdk_platforms():
    roots = []
    for env_name in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
        value = os.environ.get(env_name)
        if value and Path(value).is_dir():
            candidate = Path(value) / "platforms"
            if candidate.is_dir():
                roots.append(candidate)
    for candidate in (Path.home() / "Library/Android/sdk/platforms", Path.home() / "Android/Sdk/platforms"):
        if candidate.is_dir():
            roots.append(candidate)
    platforms = sorted({path.name for root in roots for path in root.glob("android-*") if path.is_dir()})
    return platforms


def _apk_application_id(apk, project, gradle_app_id):
    analyzers = []
    path_executable = shutil.which("apkanalyzer")
    if path_executable:
        analyzers.append([path_executable, "manifest", "application-id", str(apk)])
    sdk_roots = [
        Path(os.environ.get("ANDROID_SDK_ROOT", "")),
        Path(os.environ.get("ANDROID_HOME", "")),
        Path.home() / "Library/Android/sdk",
        Path.home() / "Android/Sdk",
    ]
    for root in sdk_roots:
        if not str(root) or not root.is_dir():
            continue
        analyzers.extend(
            [[str(candidate), "manifest", "application-id", str(apk)]
             for candidate in (root / "cmdline-tools").glob("*/bin/apkanalyzer")]
        )
        build_tools = root / "build-tools"
        if build_tools.is_dir():
            analyzers.extend(
                [[str(candidate), "dump", "badging", str(apk)]
                 for version in sorted(build_tools.iterdir(), reverse=True)
                 for candidate in [version / "aapt"] if candidate.is_file()]
            )
    for command in analyzers:
        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if proc.returncode:
            continue
        if "apkanalyzer" in Path(command[0]).name:
            value = proc.stdout.strip().splitlines()[-1:] or []
            if value and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+", value[0]):
                return value[0]
        else:
            match = re.search(r"(?m)^package: name='([^']+)'", proc.stdout)
            if match:
                return match.group(1)
    if gradle_app_id:
        gradle_file = Path(project) / "android" / "app"
        gradle_text = ""
        for suffix in ("build.gradle.kts", "build.gradle"):
            candidate = gradle_file / suffix
            if candidate.is_file():
                gradle_text = candidate.read_text(encoding="utf-8", errors="replace")
                break
        if "applicationIdSuffix" not in gradle_text:
            return gradle_app_id
    return None


def _apk_sdk_metadata(apk):
    roots = [
        Path(os.environ.get("ANDROID_SDK_ROOT", "")),
        Path(os.environ.get("ANDROID_HOME", "")),
        Path.home() / "Library/Android/sdk",
        Path.home() / "Android/Sdk",
    ]
    tools = []
    path_aapt = shutil.which("aapt")
    if path_aapt:
        tools.append(path_aapt)
    for root in roots:
        build_tools = root / "build-tools"
        if build_tools.is_dir():
            tools.extend(
                str(version / "aapt") for version in sorted(build_tools.iterdir(), reverse=True)
                if (version / "aapt").is_file()
            )
    for executable in tools:
        try:
            proc = subprocess.run(
                [executable, "dump", "badging", str(apk)],
                capture_output=True, text=True, timeout=30, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if proc.returncode:
            continue
        metadata = {}
        for key, pattern in (
            ("min_sdk", r"(?m)^sdkVersion:'(\d+)'"),
            ("target_sdk", r"(?m)^targetSdkVersion:'(\d+)'"),
        ):
            match = re.search(pattern, proc.stdout)
            metadata[key] = int(match.group(1)) if match else None
        return metadata
    return None


def _package_matches_project(project, package, application_id):
    gradle_dir = project / "android" / "app"
    text = ""
    for filename in ("build.gradle.kts", "build.gradle"):
        path = gradle_dir / filename
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            break
    suffixes = re.findall(r'applicationIdSuffix\s*(?:=\s*)?["\']([^"\']+)["\']', text)
    return package == application_id or any(package == application_id + suffix for suffix in suffixes)


def run_device_qa(project, execute=False, smoke=False, apk=None, device=None):
    project = validate_project(project)
    sdk, sdk_check = _android_gradle(project)
    apk_metadata = None
    if apk:
        apk_path = Path(apk).expanduser().resolve()
        if apk_path.is_file():
            apk_metadata = _apk_sdk_metadata(apk_path)
            if apk_metadata and sdk is not None:
                sdk["min_sdk"] = apk_metadata["min_sdk"]
                sdk["target_sdk"] = apk_metadata["target_sdk"]
                sdk["sdk_evidence"] = {
                    "status": "PASS" if apk_metadata["min_sdk"] is not None and apk_metadata["target_sdk"] is not None
                    else "PARTIAL",
                    "source": "Android APK manifest via aapt",
                }
                if apk_metadata["min_sdk"] and apk_metadata["target_sdk"]:
                    sdk_check = {
                        "status": "PASS" if apk_metadata["target_sdk"] >= apk_metadata["min_sdk"] else "FAIL",
                        "reason": "APK manifest minimum and target Android SDK values inspected",
                    }
    profiles = [
        {"profile": "compact_phone", "resolution": "720x1280", "density_dpi": 320, "status": "NOT RUN"},
        {"profile": "typical_phone", "resolution": "1080x2400", "density_dpi": 420, "status": "NOT RUN"},
        {"profile": "tablet", "resolution": "1600x2560", "density_dpi": 320, "status": "NOT RUN"},
    ]
    result = {
        "milestone": 46, "name": "Android Device Compatibility QA", "project": str(project),
        "mode": "EXECUTE" if execute else "DRY RUN", "android_sdk": sdk,
        "sdk_validation": sdk_check, "installed_sdk_platforms": _sdk_platforms(),
        "device_discovery": {"status": "NOT RUN"}, "devices": [],
        "screen_density_matrix": profiles, "smoke_test": {"status": "NOT RUN",
        "reason": "Installation and launch require --execute --smoke, a new APK, and a selected Android device."},
        "permissions": {"status": "NOT RUN", "reason": "Permission behavior requires app-specific scenarios and human/device interaction."},
        "untested_devices": profiles,
    }
    if execute:
        devices, discovery = _flutter_android_devices()
        result["device_discovery"] = discovery
        result["devices"] = devices
        result["untested_devices"] = profiles
        if smoke:
            selected = device
            if selected and not any(item["id"] == selected for item in devices):
                result["smoke_test"] = {"status": "FAIL", "device": selected,
                                        "reason": "Requested device was not found in Flutter Android device discovery"}
            elif not selected and len(devices) != 1:
                result["smoke_test"] = {
                    "status": "NOT RUN", "reason": "Select --device when zero or multiple Android devices are connected",
                    "available_devices": [item["id"] for item in devices],
                }
            else:
                selected = selected or devices[0]["id"]
                apk_path = Path(apk).expanduser().resolve() if apk else None
                if not apk_path or not apk_path.is_file():
                    result["smoke_test"] = {"status": "BLOCKED", "device": selected,
                                            "reason": "Provide an existing app-specific APK with --apk"}
                elif not sdk or not sdk.get("application_id"):
                    result["smoke_test"] = {"status": "BLOCKED", "device": selected,
                                            "reason": "Could not determine Android applicationId from Gradle"}
                else:
                    package = _apk_application_id(apk_path, project, sdk["application_id"])
                    if not package:
                        result["smoke_test"] = {
                            "status": "BLOCKED", "device": selected,
                            "reason": "Could not inspect APK application ID safely; refusing to guess the flavor/package identity.",
                        }
                        result["overall_status"] = "PARTIAL"
                        return result
                    if not _package_matches_project(project, package, sdk["application_id"]):
                        result["smoke_test"] = {
                            "status": "BLOCKED", "device": selected, "package": package,
                            "reason": "APK application ID does not match the project's configured application ID/flavor suffix.",
                        }
                        result["overall_status"] = "PARTIAL"
                        return result
                    adb = shutil.which("adb")
                    if not adb:
                        result["smoke_test"] = {"status": "BLOCKED", "device": selected,
                                                "reason": "adb executable not found"}
                    else:
                        installed = _run_command(
                            [adb, "-s", selected, "shell", "pm", "list", "packages", package],
                            project, 20,
                        )
                        if installed["status"] != "PASS":
                            result["smoke_test"] = {"status": "FAIL", "device": selected,
                                                    "step": "check_existing_install", "evidence": installed}
                        elif any(line.strip() == f"package:{package}" for line in installed["stdout_tail"]):
                            result["smoke_test"] = {
                                "status": "BLOCKED", "device": selected,
                                "reason": "Package is already installed; refusing any install/update that could overwrite it.",
                            }
                        else:
                            install = _run_command([adb, "-s", selected, "install", str(apk_path)], project, 180)
                            result["smoke_test"] = {"device": selected, "package": package, "install": install}
                            if install["status"] == "PASS":
                                activity = _run_command(
                                    [adb, "-s", selected, "shell", "cmd", "package", "resolve-activity", "--brief", package],
                                    project, 20,
                                )
                                candidates = [
                                    line.strip() for line in activity.get("stdout_tail", [])
                                    if "/" in line and package in line
                                ]
                                if activity["status"] != "PASS" or not candidates:
                                    result["smoke_test"].update({
                                        "status": "FAIL", "launch": activity,
                                        "reason": "Installed package did not resolve to a launchable activity",
                                    })
                                else:
                                    launch = _run_command(
                                        [adb, "-s", selected, "shell", "am", "start", "-W", "-n", candidates[-1]],
                                        project, 45,
                                    )
                                    runtime = _verify_running_app(adb, selected, package, project)
                                    result["smoke_test"].update({
                                        "status": "PASS" if runtime["status"] == "PASS" else "FAIL",
                                        "launch": launch, "runtime_verification": runtime,
                                        "note": "App was installed and launched; it remains installed and was not automatically removed.",
                                    })
                            else:
                                result["smoke_test"]["status"] = install["status"]
    result["overall_status"] = (
        "FAIL" if sdk_check["status"] == "FAIL" or result["smoke_test"]["status"] == "FAIL"
        else "PASS" if sdk_check["status"] == "PASS" and result["smoke_test"]["status"] == "PASS"
        else "PARTIAL"
    )
    return result


def _dart_sources(project):
    lib = project / "lib"
    return sorted(lib.rglob("*.dart")) if lib.is_dir() else []


def _relative_luminance(color):
    channels = [int(color[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
              for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _measure_named_contrast(source, relative_path):
    pairs = (("primary", "onPrimary"), ("surface", "onSurface"),
             ("background", "onBackground"), ("error", "onError"))
    findings = []
    for foreground_name, background_name in pairs:
        pattern = re.compile(
            rf"\b{foreground_name}\s*:\s*Color\(0xFF([0-9A-Fa-f]{{6}})\)"
            rf"(?s:.{{0,700}}?)\b{background_name}\s*:\s*Color\(0xFF([0-9A-Fa-f]{{6}})\)"
        )
        for match in pattern.finditer(source):
            foreground = _relative_luminance(match.group(1))
            background = _relative_luminance(match.group(2))
            ratio = (max(foreground, background) + 0.05) / (min(foreground, background) + 0.05)
            findings.append({
                "file": relative_path, "pair": f"{foreground_name}/on{foreground_name.title()}",
                "foreground": f"#{match.group(1).upper()}",
                "background": f"#{match.group(2).upper()}",
                "contrast_ratio": round(ratio, 2),
                "threshold": 4.5,
                "status": "PASS" if ratio >= 4.5 else "REVIEW",
                "automated": True,
            })
    return findings


def run_accessibility_qa(project, execute=False, output_dir=None):
    project = validate_project(project)
    findings = []
    contrast = []
    sources = _dart_sources(project)
    for path in sources:
        try:
            source = path.read_text(encoding="utf-8")
            lines = source.splitlines()
        except (OSError, UnicodeError):
            continue
        contrast.extend(_measure_named_contrast(source, str(path.relative_to(project))))
        for index, line in enumerate(lines):
            if not INTERACTIVE.search(line):
                continue
            context = "\n".join(lines[max(0, index - 2): min(len(lines), index + 4)])
            if not SEMANTIC_LABEL.search(context):
                findings.append({
                    "severity": "REVIEW", "check": "interactive_control_semantics",
                    "file": str(path.relative_to(project)), "line": index + 1,
                    "message": "Interactive control has no nearby explicit semantic label/tooltip; verify its accessible name.",
                    "automated": True,
                })
        for index, line in enumerate(lines):
            if re.search(r"\bGestureDetector\s*\(", line) and "onTap" in "\n".join(lines[index:index + 8]):
                context = "\n".join(lines[index:index + 8])
                if "Semantics(" not in context and "semanticLabel" not in context:
                    findings.append({
                        "severity": "REVIEW", "check": "gesture_semantics",
                        "file": str(path.relative_to(project)), "line": index + 1,
                        "message": "GestureDetector with onTap lacks nearby explicit semantics; verify keyboard and screen-reader access.",
                        "automated": True,
                    })
    analyzer = None
    if execute and shutil.which("flutter"):
        log = Path(output_dir) / "flutter_analyze.log" if output_dir else None
        analyzer = _run_command(["flutter", "analyze"], project, 600, log)
    elif execute:
        analyzer = {"status": "BLOCKED", "reason": "Flutter executable not found"}
    manual = [
        "TalkBack/VoiceOver reading order and control names",
        "Text scaling at 1.3x and 2.0x; check clipping and overflow",
        "Keyboard/focus navigation and focus visibility",
        "Contrast measurement for actual foreground/background pairs",
        "Touch target size and reduced-motion behavior",
        "Form error announcements and app-specific UX review",
    ]
    return {
        "milestone": 47, "name": "Accessibility and UX QA", "project": str(project),
        "mode": "EXECUTE" if execute else "STATIC REVIEW",
        "source_files_scanned": len(sources), "automated_findings": findings,
        "contrast_measurements": contrast,
        "contrast_status": "PARTIAL" if not contrast else _status(contrast),
        "flutter_analyzer": analyzer,
        "automated_status": "PARTIAL" if findings else "PASS",
        "manual_reviews": [{"check": item, "status": "NEEDS MANUAL VERIFICATION"} for item in manual],
        "overall_status": "PARTIAL",
        "note": "Static source heuristics and flutter analyze do not establish accessibility conformance or UX quality.",
    }


def _performance_thresholds(project, cli_max_bytes=None):
    thresholds = {"max_apk_bytes": cli_max_bytes, "max_startup_ms": None, "max_frame_raster_ms": None}
    warnings = []
    config_path = project / "APP_CONFIG.json"
    if config_path.is_file():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            configured = config.get("quality", {}).get("performance", {})
            if isinstance(configured, dict):
                for key in thresholds:
                    value = configured.get(key)
                    if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
                        thresholds[key] = value
        except (OSError, json.JSONDecodeError, AttributeError, TypeError) as exc:
            warnings.append(f"Could not read performance thresholds from APP_CONFIG.json: {exc}")
    return thresholds, warnings


def _performance_flavor_args(project):
    gradle_text = ""
    for filename in ("build.gradle.kts", "build.gradle"):
        path = project / "android" / "app" / filename
        if path.is_file():
            gradle_text = path.read_text(encoding="utf-8", errors="replace")
            break
    has_dev_flavor = 'create("development")' in gradle_text or re.search(
        r"(?m)^\s*development\s*\{", gradle_text
    )
    return ["--flavor", "development", "--dart-define=APP_ENV=development"] if has_dev_flavor else []


def _startup_smoke(project, apk, device, application_id, output_dir, thresholds):
    devices, discovery = _flutter_android_devices()
    if discovery["status"] != "PASS":
        return {"status": "NOT RUN", "reason": discovery.get("reason", "No Android device available")}
    if device and not any(item["id"] == device for item in devices):
        return {"status": "FAIL", "device": device, "reason": "Requested Android device is unavailable"}
    serial = device or (devices[0]["id"] if len(devices) == 1 else None)
    if not serial:
        return {"status": "NOT RUN", "reason": "Select --device when multiple Android devices are connected"}
    package = _apk_application_id(apk, project, application_id)
    if not package or not _package_matches_project(project, package, application_id):
        return {"status": "BLOCKED", "device": serial,
                "reason": "Profile APK identity could not be matched to the project"}
    adb = shutil.which("adb")
    if not adb:
        return {"status": "BLOCKED", "device": serial, "reason": "adb executable not found"}
    installed = _run_command([adb, "-s", serial, "shell", "pm", "list", "packages", package], project, 20)
    if installed["status"] != "PASS":
        return {"status": "FAIL", "step": "check_existing_install", "evidence": installed}
    if any(line.strip() == f"package:{package}" for line in installed["stdout_tail"]):
        return {"status": "BLOCKED", "device": serial,
                "reason": "Package is already installed; refusing to overwrite or update it."}
    install = _run_command([adb, "-s", serial, "install", str(apk)], project, 180)
    if install["status"] != "PASS":
        return {"status": install["status"], "step": "install", "evidence": install}
    resolved = _run_command(
        [adb, "-s", serial, "shell", "cmd", "package", "resolve-activity", "--brief", package],
        project, 20,
    )
    activities = [line.strip() for line in resolved.get("stdout_tail", []) if "/" in line and package in line]
    if resolved["status"] != "PASS" or not activities:
        return {"status": "FAIL", "step": "resolve_activity", "evidence": resolved}
    launch = _run_command(
        [adb, "-s", serial, "shell", "am", "start", "-W", "-n", activities[-1]],
        project, 60,
    )
    timings = {}
    for line in launch.get("stdout_tail", []):
        match = re.match(r"\s*(TotalTime|WaitTime|ThisTime):\s*(\d+)", line)
        if match:
            timings[match.group(1)] = int(match.group(2))
    runtime = _verify_running_app(adb, serial, package, project)
    metric_name = "TotalTime" if "TotalTime" in timings else "WaitTime" if "WaitTime" in timings else None
    if launch["status"] != "PASS" or not metric_name or runtime["status"] != "PASS":
        return {"status": "FAIL", "step": "launch", "evidence": launch,
                "runtime_verification": runtime,
                "reason": "Android did not provide a successful launch, actual timing, and foreground process evidence"}
    measured = timings[metric_name]
    maximum = thresholds.get("max_startup_ms")
    android_status_timeout = any(line.strip() == "Status: timeout" for line in launch["stdout_tail"])
    status = "FAIL" if maximum is not None and measured > maximum else (
        "PARTIAL" if android_status_timeout else "PASS"
    )
    return {
        "status": status, "device": serial, "package": package, "timings_ms": timings,
        "metric": metric_name, "runtime_verification": runtime,
        "threshold_ms": maximum,
        "note": "Cold first launch after install; app remains installed. PARTIAL indicates Android returned Status: timeout despite foreground verification.",
    }


def _verify_running_app(adb, serial, package, project):
    process = _run_command([adb, "-s", serial, "shell", "pidof", package], project, 20)
    activity = _run_command(
        [adb, "-s", serial, "shell", "dumpsys", "activity", "activities"],
        project, 30, include_stdout=True,
    )
    activity_output = activity.pop("_stdout", "")
    foreground = any(
        package in line and ("topResumedActivity" in line or "mResumedActivity" in line)
        for line in activity_output.splitlines()
    )
    running = process["status"] == "PASS" and any(
        token.isdigit() for line in process["stdout_tail"] for token in line.split()
    )
    return {
        "status": "PASS" if running and foreground else "FAIL",
        "process_running": running, "foreground_activity": foreground,
        "pidof": process, "activity_dump_status": activity["status"],
        "reason": None if running and foreground else "App process or foreground activity was not confirmed",
    }


def run_performance_qa(project, execute=False, output_dir=None, max_apk_bytes=None,
                       startup_smoke=False, device=None):
    project = validate_project(project)
    thresholds, threshold_warnings = _performance_thresholds(project, max_apk_bytes)
    result = {
        "milestone": 48, "name": "Performance and Stability", "project": str(project),
        "mode": "EXECUTE" if execute else "DRY RUN", "thresholds": thresholds,
        "profile_build": {"status": "NOT RUN"},
        "app_size": {"status": "NOT RUN"},
        "startup": {"status": "NOT RUN", "reason": "Pass --startup-smoke with --execute to measure a first launch on an Android device."},
        "threshold_warnings": threshold_warnings,
        "frame_memory_profile": {"status": "NOT RUN", "reason": "Flutter DevTools/trace profiling was not run."},
        "crash_logs": {"status": "NOT RUN", "reason": "No app-specific crash collection service is configured."},
    }
    if execute:
        flutter = shutil.which("flutter")
        if not flutter:
            result["profile_build"] = {"status": "BLOCKED", "reason": "Flutter executable not found"}
        else:
            log = Path(output_dir) / "profile_build.log" if output_dir else None
            command = [flutter, "build", "apk", "--profile", "--no-pub"]
            command.extend(_performance_flavor_args(project))
            build = _run_command(command, project, 1800, log)
            result["profile_build"] = build
            if build["status"] == "PASS":
                candidates = sorted(
                    (project / "build" / "app" / "outputs" / "flutter-apk").glob("*.apk"),
                    key=lambda path: path.stat().st_mtime,
                    reverse=True,
                )
                if candidates:
                    apk = candidates[0]
                    size = apk.stat().st_size
                    max_bytes = thresholds["max_apk_bytes"]
                    result["app_size"] = {
                        "status": "PASS" if max_bytes is None or size <= max_bytes else "FAIL",
                        "path": str(apk), "size_bytes": size,
                        "sha256": _sha256(apk),
                        "threshold_bytes": max_bytes,
                        "note": "Profile APK byte size is measured; it is not an installed-size estimate.",
                    }
                else:
                    result["app_size"] = {"status": "FAIL", "reason": "Successful profile build produced no APK at the expected Flutter output path"}
                if startup_smoke and (sdk_identity := _android_gradle(project)[0]):
                    result["startup"] = _startup_smoke(
                        project, candidates[0], device, sdk_identity.get("application_id"),
                        output_dir, thresholds,
                    ) if candidates else {"status": "NOT RUN", "reason": "Profile APK was not found"}
            elif startup_smoke:
                result["startup"] = {"status": "NOT RUN", "reason": "Profile APK build failed; startup was not attempted."}
    elif startup_smoke:
        result["startup"] = {"status": "NOT RUN", "reason": "Startup measurement requires --execute."}
    evidence = [result["profile_build"], result["app_size"], result["startup"]]
    result["overall_status"] = "FAIL" if any(item.get("status") == "FAIL" for item in evidence) else "PARTIAL"
    if any(item.get("status") == "BLOCKED" for item in evidence):
        result["overall_status"] = "PARTIAL"
    result["note"] = "Startup, frame, memory and crash metrics remain NOT RUN unless actual profiling/collection evidence is attached."
    return result


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _lock_inventory(project):
    lock = project / "pubspec.lock"
    if not lock.is_file():
        return [], {"status": "NOT RUN", "reason": "pubspec.lock not found"}
    text = lock.read_text(encoding="utf-8", errors="replace")
    packages = []
    blocks = re.finditer(r"(?ms)^  ([A-Za-z0-9_.-]+):\n(.*?)(?=^  [A-Za-z0-9_.-]+:\n|^sdks:\s*$|\Z)", text)
    for match in blocks:
        version = re.search(r'(?m)^\s+version:\s*["\']?([^"\'\s]+)', match.group(2))
        if version:
            dependency = re.search(r'(?m)^\s+dependency:\s*["\']?([^"\'\s]+)', match.group(2))
            source = re.search(r"(?m)^\s+source:\s*([^\s#]+)", match.group(2))
            dependency_kind = dependency.group(1) if dependency else "unknown"
            kind = "direct" if dependency_kind.startswith("direct") else dependency_kind
            packages.append({
                "name": match.group(1), "version": version.group(1),
                "kind": kind, "source": source.group(1) if source else "unknown",
            })
    return packages, {"status": "PASS" if packages else "PARTIAL",
                      "reason": "Static pubspec.lock inventory; package registry/CVE status is not implied"}


def _package_licenses(project, package_names):
    config_path = project / ".dart_tool" / "package_config.json"
    roots = {}
    if config_path.is_file():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            for item in config.get("packages", []):
                root_uri = item.get("rootUri")
                if root_uri:
                    parsed = urlparse(root_uri)
                    if parsed.scheme == "file":
                        package_root = Path(url2pathname(unquote(parsed.path)))
                    else:
                        package_root = Path(root_uri)
                        if not package_root.is_absolute():
                            package_root = config_path.parent / package_root
                    roots[item["name"]] = package_root.resolve()
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    inventory = []
    for package in package_names:
        root = roots.get(package["name"])
        license_files = []
        declared = None
        if root and root.is_dir():
            license_files = [path.name for pattern in ("LICENSE", "LICENSE.*", "COPYING", "COPYING.*")
                             for path in root.glob(pattern) if path.is_file()]
            pubspec = root / "pubspec.yaml"
            if pubspec.is_file():
                match = re.search(r"(?m)^license:\s*([^\s#]+)", pubspec.read_text(encoding="utf-8", errors="replace"))
                declared = match.group(1).strip("'\"") if match else None
        inventory.append({
            **package, "declared_license": declared,
            "license_files": sorted(set(license_files)),
            "status": "REVIEW" if declared or license_files else "UNKNOWN",
        })
    return inventory


def _cyclonedx(project, packages):
    components = [{
        "type": "library", "name": item["name"], "version": item["version"],
        "purl": f"pkg:pub/{item['name']}@{item['version']}",
        "scope": "excluded" if item.get("kind") == "dev" else "required",
    } for item in sorted(packages, key=lambda value: value["name"])]
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": {"type": "application", "name": project.name},
            "tools": [{"vendor": "MyAppFactory", "name": "quality_qa_engine.py"}],
        },
        "components": components,
    }


def run_dependency_audit(project, execute=False, output_dir=None,
                         vulnerability_scan=False, gradle_inventory=False):
    project = validate_project(project)
    packages, inventory_status = _lock_inventory(project)
    pub_deps = {"status": "NOT RUN", "reason": "Pass --execute to collect Flutter's resolved dependency graph."}
    if execute:
        flutter = shutil.which("flutter")
        if not flutter:
            pub_deps = {"status": "BLOCKED", "reason": "Flutter executable not found"}
        else:
            log = Path(output_dir) / "pub_deps.log" if output_dir else None
            command = _run_command(
                [flutter, "pub", "deps", "--json"], project, 900, log, include_stdout=True,
            )
            pub_deps = command
            if command["status"] == "PASS":
                try:
                    parsed = json.loads(command["_stdout"])
                    resolved = parsed.get("packages", [])
                    packages = [
                        {"name": item["name"], "version": item["version"],
                         "kind": item.get("kind", "unknown"), "source": item.get("source", "unknown")}
                        for item in resolved
                        if item.get("name") and item.get("version") and item.get("kind") != "root"
                    ]
                except (json.JSONDecodeError, AttributeError, KeyError, TypeError):
                    pub_deps["status"] = "FAIL"
                    pub_deps["error"] = "flutter pub deps did not return valid JSON package inventory"
            command.pop("_stdout", None)

    licenses = _package_licenses(project, packages)
    scanner_results = []
    available_scanners = {
        scanner: shutil.which(scanner) for scanner in ("osv-scanner", "trivy")
    }
    if vulnerability_scan:
        if not execute:
            scanner_results.append({"status": "NOT RUN", "reason": "Pass --execute and --vulnerability-scan explicitly"})
        else:
            for scanner, executable in available_scanners.items():
                if not executable:
                    continue
                if scanner == "osv-scanner":
                    command = [executable, "scan", "source", "-r", str(project), "--format", "json"]
                else:
                    command = [executable, "fs", "--scanners", "vuln", "--format", "json", str(project)]
                log = Path(output_dir) / f"{scanner}.log" if output_dir else None
                scan = _run_command(command, project, 1800, log)
                scan["execution_status"] = scan["status"]
                if scan["status"] == "PASS":
                    scan["status"] = "PARTIAL"
                    scan["reason"] = "Scanner executed; findings require interpretation and are not legal approval."
                scanner_results.append(scan)
            if not scanner_results:
                scanner_results.append({
                    "status": "NOT RUN",
                    "reason": "Neither osv-scanner nor trivy is installed; no CVE scan was performed.",
                })
    else:
        scanner_results.append({
            "status": "NOT RUN", "reason": "Known-vulnerability scanning was not requested.",
            "available_scanners": {name: bool(path) for name, path in available_scanners.items()},
        })

    gradle_result = {"status": "NOT RUN", "reason": "Gradle dependency inventory was not requested."}
    if gradle_inventory:
        wrapper = project / "android" / "gradlew"
        if not wrapper.is_file():
            gradle_result = {"status": "NOT RUN", "reason": "Android Gradle wrapper not found"}
        elif not execute:
            gradle_result = {"status": "NOT RUN", "reason": "Pass --execute to run Gradle dependency inventory"}
        else:
            gradle_result = _run_command(
                [str(wrapper), ":app:dependencies", "--configuration", "releaseRuntimeClasspath"],
                project / "android", 1800,
                Path(output_dir) / "gradle_dependencies.log" if output_dir else None,
            )

    bom = _cyclonedx(project, packages) if packages else None
    if bom is not None and output_dir:
        bom_path = Path(output_dir) / "bom.cdx.json"
        bom_path.write_text(json.dumps(bom, indent=2) + "\n", encoding="utf-8")
    unknown_licenses = [item["name"] for item in licenses if item["status"] == "UNKNOWN"]
    vulnerability_status = _status(scanner_results)
    status_items = [inventory_status, pub_deps, gradle_result]
    overall = "FAIL" if any(item.get("status") == "FAIL" for item in status_items + scanner_results) else "PARTIAL"
    return {
        "milestone": 49, "name": "Dependency, Vulnerability and License Audit",
        "project": str(project), "mode": "EXECUTE" if execute else "STATIC INVENTORY",
        "flutter_dependencies": packages, "lock_inventory": inventory_status,
        "flutter_pub_deps": pub_deps, "android_gradle_dependencies": gradle_result,
        "licenses": licenses,
        "license_status": "PARTIAL" if unknown_licenses or licenses else "NOT RUN",
        "unknown_license_packages": unknown_licenses,
        "vulnerability_scan": {
            "status": vulnerability_status, "results": scanner_results,
            "note": "Static inventory is not a vulnerability scan. Scanner exit results are evidence only and not a legal/license approval.",
        },
        "sbom": {"status": "PASS" if bom else "NOT RUN",
                 "format": "CycloneDX 1.5", "path": str(Path(output_dir) / "bom.cdx.json") if bom and output_dir else None,
                 "components": len(packages)},
        "overall_status": overall,
        "note": "No legal approval is asserted. CVE scan results are separate from package inventory and require interpretation.",
    }


def run_checks(project, checks, execute=False, output_dir=None, device=None,
               smoke=False, apk=None, max_apk_bytes=None, startup_smoke=False,
               vulnerability_scan=False, gradle_inventory=False):
    project = validate_project(project)
    selected = ("tests", "device", "accessibility", "performance", "dependencies") if checks == "all" else (checks,)
    report = {
        "tool": "MyAppFactory Quality QA Engine", "schema_version": 1,
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8],
        "project": str(project), "mode": "EXECUTE" if execute else "DRY RUN",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "milestones": {},
        "safety": {
            "operations_are_project_scoped": True,
            "dry_run_default": True,
            "release_or_upload_performed": False,
            "signing_behavior_modified": False,
        },
    }
    for check in selected:
        if check == "tests":
            result = run_test_engine(project, execute, output_dir, device)
        elif check == "device":
            result = run_device_qa(project, execute, smoke, apk, device)
        elif check == "accessibility":
            result = run_accessibility_qa(project, execute, output_dir)
        elif check == "performance":
            result = run_performance_qa(
                project, execute, output_dir, max_apk_bytes, startup_smoke, device,
            )
        else:
            result = run_dependency_audit(
                project, execute, output_dir, vulnerability_scan, gradle_inventory,
            )
        report["milestones"][str(result["milestone"])] = result
    statuses = [item["overall_status"] for item in report["milestones"].values()]
    report["overall_status"] = (
        "FAIL" if "FAIL" in statuses else
        "PASS" if statuses and all(status == "PASS" for status in statuses) else "PARTIAL"
    )
    return report


def create_output_dir(project, report_path=None):
    root = project / "build" / "factory_quality_qa"
    if report_path:
        target = Path(report_path).expanduser()
        target = (project / target).resolve() if not target.is_absolute() else target.resolve()
        if not target.is_relative_to(root.resolve()):
            raise ValueError(f"Report path must be inside the project QA output directory: {root}")
        if target.exists():
            raise FileExistsError(f"Refusing to overwrite existing QA report/output: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        return target.parent, target
    root.mkdir(parents=True, exist_ok=True)
    output = root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8])
    output.mkdir()
    return output, output / "quality_qa_report.json"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--check", choices=("tests", "device", "accessibility", "performance", "dependencies", "all"),
                        default="all")
    parser.add_argument("--execute", action="store_true", help="Run Flutter/Android commands; dry-run is the default")
    parser.add_argument("--device", help="Flutter/adb device serial; required if multiple devices are connected")
    parser.add_argument("--smoke", action="store_true", help="Install once and launch only when explicitly requested with --execute")
    parser.add_argument("--apk", type=Path, help="App-specific APK used with --smoke; package already installed is refused")
    parser.add_argument("--max-apk-bytes", type=int, help="Optional measured profile APK size ceiling")
    parser.add_argument("--startup-smoke", action="store_true",
                        help="After profile build, install only if absent and measure Android am start -W cold-start time")
    parser.add_argument("--vulnerability-scan", action="store_true", help="Explicitly run an installed osv-scanner or trivy")
    parser.add_argument("--gradle-inventory", action="store_true", help="Explicitly run Android releaseRuntimeClasspath dependency inventory")
    parser.add_argument("--report", type=Path, help="New report path inside build/factory_quality_qa; existing files are never overwritten")
    args = parser.parse_args(argv)
    if args.smoke and (not args.execute or not args.apk):
        parser.error("--smoke requires --execute and --apk")
    if args.startup_smoke and not args.execute:
        parser.error("--startup-smoke requires --execute")
    if args.max_apk_bytes is not None and args.max_apk_bytes <= 0:
        parser.error("--max-apk-bytes must be a positive integer")
    try:
        project = validate_project(args.project)
        output_dir = None
        report_path = None
        if args.execute or args.report:
            output_dir, report_path = create_output_dir(project, args.report)
        report = run_checks(
            project, args.check, args.execute, output_dir, args.device, args.smoke,
            args.apk, args.max_apk_bytes, args.startup_smoke,
            args.vulnerability_scan, args.gradle_inventory,
        )
        if report_path:
            report["report_path"] = str(report_path)
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 2 if report["overall_status"] == "FAIL" else 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"overall_status": "FAIL", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
