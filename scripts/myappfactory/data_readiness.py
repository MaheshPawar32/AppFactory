"""Milestone 43 — Data, offline and backup readiness.

- Detects storage engines (Hive, SQLite/sqflite, Drift, Isar, shared_preferences,
  Supabase, Firebase).
- Extracts a schema snapshot from source (Hive type/field ids, SQLite CREATE
  TABLE + version, Drift schemaVersion) and diffs it against the previous
  snapshot stored for this app to flag unsafe migrations.
- Discovers persistence / migration / backup / offline tests and runs them on --execute.
- Device workflows (debuggable builds only): app-data backup via `run-as`,
  approval-gated restore, and an offline launch simulation that always restores
  connectivity.
"""
from __future__ import annotations

import json
import re
import tarfile
import time
from datetime import datetime, timezone
from pathlib import Path

from . import reports as R
from .approvals import ApprovalStore
from .context import AppContext, IsolationError
from .project import all_dependency_names, dart_sources, line_of, read_text
from .runner import run, run_binary

ENGINES = {
    "hive": "hive", "hive_flutter": "hive", "hive_ce": "hive", "sqflite": "sqlite", "sqlite3": "sqlite",
    "drift": "drift", "isar": "isar", "shared_preferences": "shared_preferences",
    "supabase_flutter": "supabase", "cloud_firestore": "firebase", "firebase_database": "firebase",
}
TEST_PATTERNS = {
    "persistence": r"persist|storage|repository|database|hive|sqflite|dao|cache",
    "migration": r"migrat|schema|upgrade",
    "backup_restore": r"backup|restore|export|import",
    "offline": r"offline|network.?fail|no.?connection|connectivity|timeout",
    "integrity": r"integrity|corrupt|malformed|invalid.?data",
}


def detect_engines(app) -> list[str]:
    return sorted({ENGINES[d] for d in all_dependency_names(app.root) if d in ENGINES})


def extract_schema(app) -> dict:
    """Best-effort schema snapshot from Dart source."""
    hive_types, sqlite_tables, sqlite_versions, drift_versions, problems = {}, {}, [], [], []
    for path in dart_sources(app.root):
        if not str(path.relative_to(app.root)).startswith("lib"):
            continue
        text = read_text(path) or ""
        relative = str(path.relative_to(app.root))
        for match in re.finditer(r"@HiveType\(\s*typeId:\s*(\d+)[^)]*\)\s*class\s+(\w+)([\s\S]*?)(?=@HiveType|\Z)", text):
            type_id, cls, body = int(match.group(1)), match.group(2), match.group(3)
            fields = [(int(i), n) for i, n in re.findall(r"@HiveField\(\s*(\d+)[^)]*\)\s*(?:final\s+|late\s+)?[\w<>?, ]+?\s+(\w+)\s*[;=]", body)]
            ids = [i for i, _ in fields]
            if len(ids) != len(set(ids)):
                problems.append({"file": relative, "line": line_of(text, match.start()),
                                 "problem": f"Duplicate @HiveField index in {cls}"})
            if type_id in {v["type_id"] for v in hive_types.values()}:
                problems.append({"file": relative, "line": line_of(text, match.start()),
                                 "problem": f"Hive typeId {type_id} reused by {cls}"})
            hive_types[cls] = {"type_id": type_id, "fields": {str(i): n for i, n in fields}, "file": relative}
        for match in re.finditer(r"CREATE TABLE(?: IF NOT EXISTS)?\s+[`'\"]?(\w+)[`'\"]?\s*\(([^;]*?)\)\s*['\"]", text, re.I):
            columns = [c.strip().split()[0].strip("`'\"") for c in match.group(2).split(",")
                       if c.strip() and not re.match(r"(?i)\s*(primary|foreign|unique|constraint|check)\b", c)]
            sqlite_tables[match.group(1)] = {"columns": columns, "file": relative}
        for match in re.finditer(r"openDatabase\(([\s\S]{0,600}?)\)\s*;", text):
            args = match.group(1)
            version = re.search(r"version:\s*(\d+)", args)
            sqlite_versions.append({"file": relative, "version": int(version.group(1)) if version else None,
                                    "on_upgrade": "onUpgrade" in args, "on_downgrade": "onDowngrade" in args})
        for match in re.finditer(r"int\s+get\s+schemaVersion\s*=>\s*(\d+)", text):
            drift_versions.append({"file": relative, "version": int(match.group(1)),
                                   "migration_strategy": "MigrationStrategy" in text})
    return {"hive_types": hive_types, "sqlite_tables": sqlite_tables, "sqlite_databases": sqlite_versions,
            "drift": drift_versions, "problems": problems}


def diff_schema(previous: dict, current: dict) -> list[dict]:
    """Changes that can corrupt or lose existing user data."""
    risks = []
    for cls, old in (previous.get("hive_types") or {}).items():
        new = current["hive_types"].get(cls)
        if not new:
            risks.append({"severity": "high", "change": f"Hive type {cls} removed; stored objects become unreadable"})
            continue
        if new["type_id"] != old["type_id"]:
            risks.append({"severity": "high", "change": f"Hive {cls} typeId {old['type_id']}→{new['type_id']}"})
        for index, name in old["fields"].items():
            if index not in new["fields"]:
                risks.append({"severity": "medium", "change": f"Hive {cls} field #{index} ({name}) removed; never reuse index {index}"})
            elif new["fields"][index] != name:
                risks.append({"severity": "high", "change": f"Hive {cls} field #{index} reused: {name}→{new['fields'][index]}"})
    old_versions = {d["file"]: d["version"] for d in previous.get("sqlite_databases", [])}
    for table, old in (previous.get("sqlite_tables") or {}).items():
        new = current["sqlite_tables"].get(table)
        changed = not new or set(old["columns"]) - set(new["columns"]) or (new and set(new["columns"]) - set(old["columns"]))
        if changed:
            bumped = any(d["version"] and old_versions.get(d["file"]) and d["version"] > old_versions[d["file"]]
                         for d in current["sqlite_databases"])
            if not bumped:
                risks.append({"severity": "high", "change": f"SQLite table {table} changed without a database version bump"})
    return risks


def _snapshot_path(app):
    return app.state_path("data", "schema_snapshot.json")


def discover_data_tests(app) -> dict:
    found = {k: [] for k in TEST_PATTERNS}
    for path in dart_sources(app.root):
        if not path.name.endswith("_test.dart"):
            continue
        relative = str(path.relative_to(app.root))
        haystack = relative.lower() + " " + " ".join(re.findall(r"(?:test|testWidgets|group)\(\s*['\"]([^'\"]+)",
                                                                  (read_text(path) or "").lower()))
        for kind, pattern in TEST_PATTERNS.items():
            if re.search(pattern, haystack):
                found[kind].append(relative)
    return found


def offline_heuristics(app) -> list[dict]:
    """Network calls in files with no error handling — likely crash/blank-screen when offline."""
    issues = []
    for path in dart_sources(app.root):
        relative = str(path.relative_to(app.root))
        if not relative.startswith("lib"):
            continue
        text = read_text(path) or ""
        calls = list(re.finditer(r"\b(http\.(get|post|put|delete)|dio\.(get|post|put|delete)|\.from\(['\"]\w+['\"]\)\.select)\(", text))
        if calls and not re.search(r"\btry\s*\{|\.catchError\(|on\s+\w*(Socket|Http|Dio|Timeout)\w*Exception", text):
            issues.append({"file": relative, "line": line_of(text, calls[0].start()),
                           "message": "Network call without visible error handling"})
    return issues


def run_data_readiness(app: AppContext, execute=False, update_snapshot=False) -> dict:
    engines = detect_engines(app)
    schema = extract_schema(app)
    checks = [R.check("Storage engines", R.PASS if engines else R.NOT_APPLICABLE,
                      ", ".join(engines) or "No persistence package detected")]
    if schema["problems"]:
        checks.append(R.check("Schema definitions", R.FAIL, "; ".join(p["problem"] for p in schema["problems"])))
    elif schema["hive_types"] or schema["sqlite_tables"] or schema["drift"]:
        checks.append(R.check("Schema definitions", R.PASS,
                              f"{len(schema['hive_types'])} Hive types, {len(schema['sqlite_tables'])} SQLite tables, "
                              f"{len(schema['drift'])} Drift DBs"))
    for db in schema["sqlite_databases"]:
        if db["version"] and db["version"] > 1 and not db["on_upgrade"]:
            checks.append(R.check(f"SQLite migration ({db['file']})", R.FAIL, f"version {db['version']} without onUpgrade"))
    for db in schema["drift"]:
        if db["version"] > 1 and not db["migration_strategy"]:
            checks.append(R.check(f"Drift migration ({db['file']})", R.FAIL, f"schemaVersion {db['version']} without MigrationStrategy"))
    snapshot_file = _snapshot_path(app)
    risks = []
    if snapshot_file.is_file():
        previous = json.loads(snapshot_file.read_text(encoding="utf-8"))
        risks = diff_schema(previous.get("schema", {}), schema)
        checks.append(R.check("Migration safety vs last snapshot", R.FAIL if any(r["severity"] == "high" for r in risks)
                              else (R.WARN if risks else R.PASS),
                              "; ".join(r["change"] for r in risks) or f"No breaking changes since {previous.get('taken_at')}"))
    else:
        checks.append(R.check("Migration safety vs last snapshot", R.NOT_RUN,
                              "No baseline yet; run with --update-snapshot after a verified release"))
    if update_snapshot:
        snapshot_file.parent.mkdir(parents=True, exist_ok=True)
        snapshot_file.write_text(json.dumps({"taken_at": R.now(), "schema": schema}, indent=2), encoding="utf-8")
    offline = offline_heuristics(app)
    checks.append(R.check("Offline error handling (static)", R.WARN if offline else R.PASS,
                          f"{len(offline)} file(s) with unguarded network calls" if offline else "No unguarded network calls found"))
    tests = discover_data_tests(app)
    for kind, files in tests.items():
        applicable = engines or kind == "offline"
        checks.append(R.check(f"Tests: {kind}", R.PASS if files else (R.NOT_RUN if applicable else R.NOT_APPLICABLE),
                              ", ".join(files) or "None found"))
    commands = []
    test_files = sorted({f for files in tests.values() for f in files})
    if execute and test_files:
        result = run(["flutter", "test", *test_files], app.root, timeout=900)
        commands.append(result.to_dict())
        checks.append(R.check("Data test execution", result.status, f"exit {result.returncode}"))
    remote = [e for e in engines if e in ("supabase", "firebase")]
    if remote:
        checks.append(R.check("Remote data rules / backups", R.MANUAL,
                              f"{', '.join(remote)}: verify security rules/RLS and provider backups in the console"))
    return R.make_report(app, "data-readiness", "Data, offline & backup readiness", checks, milestone=43,
                         data={"engines": engines, "schema": schema, "migration_risks": risks,
                               "offline_issues": offline, "tests": tests}, commands=commands,
                         limitations=["Schema extraction is regex-based and covers common Hive/sqflite/Drift patterns."],
                         manual=["Upgrade-install over the previous release on a device and confirm data survives.",
                                 "Run the app in airplane mode through each primary journey."])


# --- Device workflows ------------------------------------------------------

def _adb(serial):
    return ["adb", "-s", serial] if serial else ["adb"]


def _device_cwd(app) -> Path:
    """Device commands run from the app's state dir, which may not exist yet."""
    app.state_dir.mkdir(parents=True, exist_ok=True)
    return app.state_dir


def backup_device_data(app: AppContext, package: str, serial=None) -> Path:
    """Copy a debuggable app's private data to the factory state dir (never into the app tree)."""
    if not re.fullmatch(r"[A-Za-z][\w.]+", package or ""):
        raise ValueError("Invalid package")
    if package != app.package_name and not package.startswith(app.package_name + "."):
        raise IsolationError(f"{package} does not belong to {app.app_id}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = app.state_path("data", "device_backups", f"{package}-{stamp}.tar")
    target.parent.mkdir(parents=True, exist_ok=True)
    code, data, stderr = run_binary([*_adb(serial), "exec-out", "run-as", package, "tar", "-cf", "-", "."],
                                    _device_cwd(app))
    if code != 0 or not data:
        raise RuntimeError(f"Backup failed (debuggable build required): {stderr.strip()[:200]}")
    target.write_bytes(data)
    try:
        with tarfile.open(target) as archive:
            archive.getmembers()  # integrity: raises if the archive is malformed
    except tarfile.TarError:
        target.unlink()
        raise RuntimeError("Device returned a malformed archive; backup discarded")
    return target


def restore_device_data(app: AppContext, package: str, archive: Path, serial=None, approvals=None):
    """Overwrite device app data from a backup; requires a payload-bound approval."""
    archive = app.ensure_within(archive)
    if package != app.package_name and not package.startswith(app.package_name + "."):
        raise IsolationError(f"{package} does not belong to {app.app_id}")
    approvals = approvals or ApprovalStore.for_app(app)
    approvals.require("device_data_restore", {"package": package, "archive": str(archive), "serial": serial},
                      reason="Restore overwrites the app's current on-device data")
    code, _, stderr = run_binary([*_adb(serial), "exec-in", "run-as", package, "tar", "-xf", "-"],
                                 _device_cwd(app), stdin_bytes=archive.read_bytes())
    if code != 0:
        raise RuntimeError(f"Restore failed: {stderr.strip()[:200]}")
    return True


def simulate_offline_launch(app: AppContext, package: str, serial=None, seconds=8) -> dict:
    """Enable airplane mode, launch the app, collect crashes, ALWAYS restore connectivity."""
    if package != app.package_name and not package.startswith(app.package_name + "."):
        raise IsolationError(f"{package} does not belong to {app.app_id}")
    adb = _adb(serial)
    outcome = {"package": package, "crashed": None, "restored": False}
    run([*adb, "logcat", "-c"], _device_cwd(app), timeout=30)
    try:
        run([*adb, "shell", "cmd", "connectivity", "airplane-mode", "enable"], _device_cwd(app), timeout=30)
        launch = run([*adb, "shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"],
                     _device_cwd(app), timeout=60)
        outcome["launched"] = launch.ok
        time.sleep(seconds)
        log = run([*adb, "logcat", "-d", "-b", "crash"], _device_cwd(app), timeout=60)
        outcome["crashed"] = package in log.stdout
        pid = run([*adb, "shell", "pidof", package], _device_cwd(app), timeout=30)
        outcome["alive"] = bool(pid.stdout.strip())
    finally:
        restore = run([*adb, "shell", "cmd", "connectivity", "airplane-mode", "disable"], _device_cwd(app), timeout=30)
        outcome["restored"] = restore.ok
    return outcome
