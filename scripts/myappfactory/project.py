"""Read-only Flutter project inspection shared by milestone tools (no YAML dependency)."""
from __future__ import annotations

import json
import re
from pathlib import Path

SKIP_DIRS = {"build", ".dart_tool", ".gradle", ".idea", ".git", "node_modules", "Pods",
             "ephemeral", ".symlinks", ".pub-cache", ".cxx", "DerivedData"}
TEXT_SUFFIXES = {".dart", ".kt", ".kts", ".gradle", ".java", ".xml", ".json", ".yaml", ".yml",
                 ".properties", ".env", ".plist", ".swift", ".txt", ".md", ".sql", ".arb", ".html",
                 ".js", ".ts", ".toml", ".cfg", ".ini", ""}
MAX_TEXT_BYTES = 2_000_000


def iter_files(root: Path, suffixes=None, subdir=None):
    base = root / subdir if subdir else root
    if not base.exists():
        return
    stack = [base]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if entry.name not in SKIP_DIRS:
                    stack.append(entry)
            elif suffixes is None or entry.suffix in suffixes or entry.name in suffixes:
                yield entry


def read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_TEXT_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def dart_sources(root: Path):
    for sub in ("lib", "test", "integration_test"):
        yield from iter_files(root, {".dart"}, sub)


def pubspec_dependencies(root: Path) -> dict[str, dict]:
    """Return {'dependencies': {...}, 'dev_dependencies': {...}} with raw constraint text."""
    result = {"dependencies": {}, "dev_dependencies": {}, "dependency_overrides": {}}
    path = root / "pubspec.yaml"
    if not path.is_file():
        return result
    section = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        top = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if top:
            section = top.group(1) if top.group(1) in result else None
            continue
        if section:
            dep = re.match(r"^  ([A-Za-z0-9_]+):\s*(.*)$", line)
            if dep:
                result[section][dep.group(1)] = dep.group(2).strip().strip("'\"")
    return result


def all_dependency_names(root: Path) -> set[str]:
    deps = pubspec_dependencies(root)
    return set(deps["dependencies"]) | set(deps["dev_dependencies"])


def lock_packages(root: Path) -> dict[str, dict]:
    """Parse pubspec.lock into {name: {version, source, dependency}}."""
    path = root / "pubspec.lock"
    packages: dict[str, dict] = {}
    if not path.is_file():
        return packages
    current = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        name = re.match(r"^  ([A-Za-z0-9_]+):\s*$", line)
        if name:
            current = packages.setdefault(name.group(1), {})
            continue
        field = re.match(r"^    (version|source|dependency):\s*\"?([^\"]+)\"?\s*$", line)
        if current is not None and field:
            current[field.group(1)] = field.group(2).strip()
    return packages


def load_app_config(root: Path) -> dict:
    for candidate in (root / "APP_CONFIG.json", root / "docs" / "APP_CONFIG.json"):
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
            except (OSError, json.JSONDecodeError):
                return {}
    return {}


def android_manifests(root: Path) -> list[Path]:
    src = root / "android" / "app" / "src"
    return sorted(src.glob("*/AndroidManifest.xml")) if src.is_dir() else []


_TAG_RE = re.compile(r"<\s*(uses-permission(?:-sdk-23)?)\b([^>]*)>", re.S)
_ATTR_RE = re.compile(r"([\w:.-]+)\s*=\s*\"([^\"]*)\"")


def manifest_permissions(text: str) -> list[dict]:
    """<uses-permission> entries without an XML parser (pyexpat is not always usable).

    Comments are stripped first so commented-out permissions are not counted.
    """
    text = re.sub(r"<!--[\s\S]*?-->", "", text)
    entries = []
    for match in _TAG_RE.finditer(text):
        attrs = dict(_ATTR_RE.findall(match.group(2)))
        if attrs.get("android:name"):
            entries.append({"name": attrs["android:name"], "removed": attrs.get("tools:node") == "remove",
                            "max_sdk": attrs.get("android:maxSdkVersion")})
    return entries


def gradle_file(root: Path) -> Path | None:
    for name in ("build.gradle.kts", "build.gradle"):
        path = root / "android" / "app" / name
        if path.is_file():
            return path
    return None


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1
