"""Registered-app resolution and strict per-app path isolation.

An AppContext is the only way milestone tools address an app. It carries the
app identity, the project root and a factory-side state directory. Every path a
tool touches is validated with `resolve()` / `ensure_within()`, which follow
symlinks, so App A cannot read or write App B's files, reports or secrets.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

FACTORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = FACTORY_ROOT / "apps" / "PROJECT_REGISTRY.csv"
DEFAULT_STATE_ROOT = FACTORY_ROOT / "state"
APP_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{1,99}$")
PACKAGE_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


class IsolationError(PermissionError):
    """A path or resource belongs outside the selected app's boundary."""


class RegistryError(ValueError):
    pass


def is_within(path: Path, directory: Path) -> bool:
    try:
        Path(path).resolve().relative_to(Path(directory).resolve())
        return True
    except ValueError:
        return False


def app_id_for(package_name: str) -> str:
    if not PACKAGE_RE.fullmatch(package_name or ""):
        raise RegistryError(f"Invalid package name: {package_name!r}")
    return package_name


@dataclass(frozen=True)
class AppContext:
    app_id: str
    name: str
    package_name: str
    root: Path
    state_root: Path = field(default=DEFAULT_STATE_ROOT)
    registered: bool = True
    version: str = ""
    row: dict = field(default_factory=dict, compare=False, repr=False)

    def __post_init__(self):
        if not APP_ID_RE.fullmatch(self.app_id):
            raise RegistryError(f"Invalid app id: {self.app_id!r}")

    @property
    def state_dir(self) -> Path:
        return self.state_root / "apps" / self.app_id

    def identity(self) -> dict:
        return {"app_id": self.app_id, "app_name": self.name, "package_name": self.package_name,
                "project_root": str(self.root), "registered": self.registered}

    def resolve(self, relative) -> Path:
        """Resolve a path inside the project root; raise IsolationError otherwise."""
        candidate = Path(relative)
        candidate = candidate if candidate.is_absolute() else self.root / candidate
        return self.ensure_within(candidate)

    def ensure_within(self, path) -> Path:
        resolved = Path(path).resolve()
        if not (is_within(resolved, self.root) or is_within(resolved, self.state_dir)):
            raise IsolationError(f"{path} is outside app '{self.app_id}'")
        return resolved

    def state_path(self, *parts) -> Path:
        path = self.state_dir.joinpath(*parts)
        if not is_within(path, self.state_dir):
            raise IsolationError(f"State path escapes app '{self.app_id}': {parts}")
        return path


def _registry_rows(registry: Path):
    if not registry.is_file():
        return []
    with registry.open(newline="", encoding="utf-8-sig") as handle:
        return [row for row in csv.DictReader(handle) if (row.get("app_name") or "").strip()]


def load_registered_apps(registry=None, base=None, state_root=None) -> dict[str, AppContext]:
    """Load all registered apps; reject duplicates and overlapping project roots."""
    registry = Path(registry or DEFAULT_REGISTRY)
    base = Path(base or FACTORY_ROOT).resolve()
    state_root = Path(state_root or DEFAULT_STATE_ROOT)
    apps: dict[str, AppContext] = {}
    for row in _registry_rows(registry):
        package = (row.get("package_name") or "").strip()
        path_text = (row.get("project_path") or "").strip()
        if not path_text:
            raise RegistryError(f"{row['app_name']}: project_path is required")
        root = Path(path_text).expanduser()
        root = (root if root.is_absolute() else base / root).resolve()
        app = AppContext(app_id_for(package), row["app_name"].strip(), package, root,
                         state_root, True, (row.get("version") or "").strip(), dict(row))
        if app.app_id in apps:
            raise RegistryError(f"Duplicate package/app id in registry: {app.app_id}")
        for other in apps.values():
            if is_within(root, other.root) or is_within(other.root, root):
                raise RegistryError(f"Project roots overlap: {app.app_id} and {other.app_id}")
        apps[app.app_id] = app
    return apps


def get_app(app_id: str, registry=None, base=None, state_root=None) -> AppContext:
    apps = load_registered_apps(registry, base, state_root)
    if app_id not in apps:
        raise RegistryError(f"App not registered: {app_id}. Registered: {', '.join(sorted(apps)) or 'none'}")
    return apps[app_id]


def detect_package_name(project: Path) -> str | None:
    """Read the Android applicationId, falling back to None."""
    for name in ("build.gradle.kts", "build.gradle"):
        gradle = project / "android" / "app" / name
        if gradle.is_file():
            text = gradle.read_text(encoding="utf-8", errors="replace")
            match = re.search(r"applicationId\s*=?\s*[\"']([^\"']+)[\"']", text)
            if match:
                return match.group(1)
    return None


def adhoc_app(project, state_root=None) -> AppContext:
    """Context for an unregistered Flutter project (single-app commands and tests)."""
    root = Path(project).expanduser().resolve()
    if not (root / "pubspec.yaml").is_file():
        raise RegistryError(f"Not a Flutter project (pubspec.yaml missing): {root}")
    pubspec = (root / "pubspec.yaml").read_text(encoding="utf-8", errors="replace")
    name_match = re.search(r"(?m)^name:\s*([A-Za-z0-9_]+)", pubspec)
    name = name_match.group(1) if name_match else root.name
    package = detect_package_name(root)
    app_id = package if package and PACKAGE_RE.fullmatch(package) else f"adhoc.{name.lower()}"
    version = re.search(r"(?m)^version:\s*([^\s#]+)", pubspec)
    return AppContext(app_id, name, package or "", root, Path(state_root or DEFAULT_STATE_ROOT),
                      False, version.group(1) if version else "")


def resolve_app(app_id=None, project=None, registry=None, base=None, state_root=None) -> AppContext:
    """Prefer the registry; allow an explicit project path for unregistered apps."""
    if app_id:
        return get_app(app_id, registry, base, state_root)
    if project:
        root = Path(project).expanduser().resolve()
        for app in load_registered_apps(registry, base, state_root).values():
            if app.root == root:
                return app
        return adhoc_app(root, state_root)
    raise RegistryError("Select an app with --app <app_id> or --project <path>")
