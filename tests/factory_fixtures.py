"""Fixture builders for MyAppFactory core tests: realistic Flutter project trees."""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from myappfactory.context import AppContext  # noqa: E402

REGISTRY_HEADER = ["app_name", "package_name", "current_stage", "version", "platform", "project_path",
                   "last_analyzer_status", "last_test_status", "last_build_status", "open_blockers",
                   "next_action", "last_checked_at", "evidence_path", "notes"]

MANIFEST = """<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools">
{permissions}
    <application android:label="app"><activity android:name=".MainActivity"/></application>
</manifest>
"""

GRADLE = """plugins {{ id("com.android.application") }}
android {{
    namespace = "{package}"
    compileSdk = 36
    defaultConfig {{
        applicationId = "{package}"
        minSdk = {min_sdk}
        targetSdk = {target_sdk}
        versionCode = 1
        versionName = "1.0.0"
    }}
}}
"""


def make_flutter_app(base, name="fixture_app", package="com.test.fixture", deps=(), dev_deps=(),
                     files=None, permissions=(), config=None, lock=None, version="1.0.0+1",
                     min_sdk=24, target_sdk=36, gitignore=True):
    root = Path(base) / name
    (root / "lib").mkdir(parents=True)
    (root / "test").mkdir()
    dep_lines = "".join(f"  {d}: ^1.0.0\n" for d in deps)
    dev_lines = "".join(f"  {d}: ^1.0.0\n" for d in dev_deps)
    (root / "pubspec.yaml").write_text(
        f"name: {name}\nversion: {version}\n\nenvironment:\n  sdk: '>=3.3.0 <4.0.0'\n\n"
        f"dependencies:\n  flutter:\n    sdk: flutter\n{dep_lines}\n"
        f"dev_dependencies:\n  flutter_test:\n    sdk: flutter\n{dev_lines}", encoding="utf-8")
    lock_entries = lock if lock is not None else {d: "1.0.0" for d in deps}
    (root / "pubspec.lock").write_text("packages:\n" + "".join(
        f"  {d}:\n    dependency: \"direct main\"\n    source: hosted\n    version: \"{v}\"\n"
        for d, v in lock_entries.items()), encoding="utf-8")
    (root / "lib" / "main.dart").write_text("void main() {}\n", encoding="utf-8")
    manifest_dir = root / "android" / "app" / "src" / "main"
    manifest_dir.mkdir(parents=True)
    perm_xml = "\n".join(f'    <uses-permission android:name="{p if "." in p else "android.permission." + p}"/>'
                         for p in permissions)
    (manifest_dir / "AndroidManifest.xml").write_text(MANIFEST.format(permissions=perm_xml), encoding="utf-8")
    (root / "android" / "app" / "build.gradle.kts").write_text(
        GRADLE.format(package=package, min_sdk=min_sdk, target_sdk=target_sdk), encoding="utf-8")
    if gitignore:
        (root / ".gitignore").write_text(".env\n*.jks\n*.keystore\nkey.properties\nbuild/\n", encoding="utf-8")
    if config is not None:
        (root / "APP_CONFIG.json").write_text(json.dumps(config), encoding="utf-8")
    for relative, content in (files or {}).items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


def make_ctx(root, state_root, package=None, name=None):
    package = package or "com.test." + Path(root).name.replace("-", "_")
    return AppContext(package, name or Path(root).name, package, Path(root).resolve(), Path(state_root))


def write_registry(path, apps):
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGISTRY_HEADER)
        writer.writeheader()
        for app in apps:
            writer.writerow({k: app.get(k, "") for k in REGISTRY_HEADER})
