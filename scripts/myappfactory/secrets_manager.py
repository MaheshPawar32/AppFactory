"""Milestone 41 — Secure secrets management.

Secret values live only in (a) environment variables or CI secrets, or (b) a
per-app local store under `state/apps/<app_id>/secrets/` with 0700/0600
permissions, outside the app source tree. Reports carry names, sources and
status — never values.

Lookup order for secret NAME in app A, environment E:
  1. MYAPPFACTORY_<APPKEY>_<E>_<NAME>   (app- and environment-scoped variable)
  2. local protected store for app A / E
  3. plain NAME only when CI=true (CI runners hold one app's secrets per job)
App A therefore never resolves app B's scoped variables or local store.
"""
from __future__ import annotations

import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path

from . import reports as R
from .audit import app_audit
from .context import AppContext, IsolationError, is_within
from .project import TEXT_SUFFIXES, iter_files, load_app_config, read_text
from .redact import find_secrets

ENVIRONMENTS = ("development", "staging", "production")
NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
RELEASE_SIGNING_VARS = ("MYAPP_RELEASE_STORE_FILE", "MYAPP_RELEASE_STORE_PASSWORD",
                        "MYAPP_RELEASE_KEY_ALIAS", "MYAPP_RELEASE_KEY_PASSWORD")
DEFAULT_ROTATION_DAYS = 365
SIGNING_FILE_PATTERNS = ("*.jks", "*.keystore", "*.p12", "key.properties", "*.pem", "*.p8")
GITIGNORE_REQUIRED = (".env", "*.jks", "*.keystore", "key.properties")
# Firebase client config contains a restricted public API key; reported, not failed.
CLIENT_CONFIG_FILES = {"google-services.json", "GoogleService-Info.plist", "firebase_options.dart"}


class MissingSecret(KeyError):
    pass


def _check_env(environment):
    if environment not in ENVIRONMENTS:
        raise ValueError(f"Unknown environment: {environment}")


def _check_name(name):
    if not NAME_RE.fullmatch(name or ""):
        raise ValueError(f"Secret names must match {NAME_RE.pattern}: {name!r}")


def app_key(app: AppContext) -> str:
    return re.sub(r"[^A-Z0-9]", "_", app.app_id.upper())


def scoped_env_name(app: AppContext, environment: str, name: str) -> str:
    return f"MYAPPFACTORY_{app_key(app)}_{environment.upper()}_{name}"


class SecretStore:
    def __init__(self, app: AppContext):
        self.app = app
        self.directory = app.state_path("secrets")
        if is_within(self.directory, app.root):
            raise IsolationError("Secret store must not be inside the app source tree")

    def _file(self, environment):
        _check_env(environment)
        return self.directory / f"{environment}.json"

    def _meta_file(self):
        return self.directory / "meta.json"

    def _ensure_dir(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        os.chmod(self.directory, 0o700)

    def _read(self, path) -> dict:
        if not path.is_file():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, path, data):
        self._ensure_dir()
        temp = path.with_suffix(".tmp")
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.chmod(temp, 0o600)
        temp.replace(path)

    def names(self, environment) -> list[str]:
        return sorted(self._read(self._file(environment)))

    def get(self, environment, name):
        return self._read(self._file(environment)).get(name)

    def set(self, environment, name, value, actor="local-user"):
        _check_name(name)
        if not value:
            raise ValueError("Refusing to store an empty secret")
        data = self._read(self._file(environment))
        rotated = name in data and data[name] != value
        data[name] = value
        self._write(self._file(environment), data)
        meta = self._read(self._meta_file())
        entry = meta.setdefault(environment, {}).setdefault(name, {})
        stamp = datetime.now(timezone.utc).isoformat()
        entry.setdefault("created_at", stamp)
        if rotated or "rotated_at" not in entry:
            entry["rotated_at"] = stamp
        self._write(self._meta_file(), meta)
        app_audit(self.app).append("secret_set", actor, {"environment": environment, "name": name,
                                                         "rotated": rotated}, self.app.app_id)

    def delete(self, environment, name, actor="local-user"):
        data = self._read(self._file(environment))
        if name not in data:
            return False
        del data[name]
        self._write(self._file(environment), data)
        app_audit(self.app).append("secret_deleted", actor, {"environment": environment, "name": name},
                                   self.app.app_id)
        return True

    def metadata(self, environment) -> dict:
        return self._read(self._meta_file()).get(environment, {})

    def permission_problems(self) -> list[str]:
        problems = []
        if not self.directory.exists():
            return problems
        if stat.S_IMODE(self.directory.stat().st_mode) & 0o077:
            problems.append(f"{self.directory.name}/ is accessible to other users")
        for path in self.directory.glob("*.json"):
            if stat.S_IMODE(path.stat().st_mode) & 0o077:
                problems.append(f"{path.name} is accessible to other users")
        return problems


def lookup(app: AppContext, environment: str, name: str, environ=None):
    """Return (value, source) or (None, None). Source is a label, never the value."""
    _check_env(environment)
    environ = os.environ if environ is None else environ
    scoped = scoped_env_name(app, environment, name)
    if environ.get(scoped):
        return environ[scoped], f"env:{scoped}"
    value = SecretStore(app).get(environment, name)
    if value:
        return value, "local-store"
    if environ.get("CI", "").lower() == "true" and environ.get(name):
        return environ[name], f"ci-env:{name}"
    return None, None


def env_for_process(app, environment, names, environ=None) -> dict:
    """Values to inject into a child process; raises MissingSecret listing missing names."""
    values, missing = {}, []
    for name in names:
        value, _ = lookup(app, environment, name, environ)
        if value is None:
            missing.append(name)
        else:
            values[name] = value
    if missing:
        raise MissingSecret(", ".join(missing))
    return values


def required_secrets(app: AppContext, environment: str, include_release_signing=None) -> list[dict]:
    """Declared secrets for an environment from APP_CONFIG.json (names only)."""
    _check_env(environment)
    config = load_app_config(app.root)
    required: dict[str, dict] = {}
    for item in config.get("secrets", []) if isinstance(config.get("secrets"), list) else []:
        if isinstance(item, dict) and NAME_RE.fullmatch(str(item.get("name", ""))):
            envs = item.get("environments") or list(ENVIRONMENTS)
            if environment in envs:
                required[item["name"]] = {"name": item["name"], "purpose": item.get("purpose", ""),
                                          "required": item.get("required", True),
                                          "rotation_days": int(item.get("rotation_days", DEFAULT_ROTATION_DAYS))}
    env_section = (config.get("environments") or {}).get(environment) or {}
    for name in env_section.get("required_variables", []) if isinstance(env_section, dict) else []:
        if NAME_RE.fullmatch(str(name)):
            required.setdefault(name, {"name": name, "purpose": "environments.required_variables",
                                       "required": True, "rotation_days": DEFAULT_ROTATION_DAYS})
    if include_release_signing is None:
        include_release_signing = environment == "production"
    if include_release_signing:
        for name in RELEASE_SIGNING_VARS:
            required.setdefault(name, {"name": name, "purpose": "Android release signing",
                                       "required": True, "rotation_days": 0})
    return [required[k] for k in sorted(required)]


def validate(app: AppContext, environment: str, environ=None, include_release_signing=None) -> dict:
    checks, inventory = [], []
    store = SecretStore(app)
    problems = store.permission_problems()
    checks.append(R.check("Local store permissions", R.FAIL if problems else R.PASS,
                          "; ".join(problems) or "Store directory 0700, files 0600 (or store not created)"))
    meta = store.metadata(environment)
    now = datetime.now(timezone.utc)
    for item in required_secrets(app, environment, include_release_signing):
        value, source = lookup(app, environment, item["name"], environ)
        status = R.PASS if value else (R.FAIL if item["required"] else R.WARN)
        detail = f"Resolved from {source}" if value else "Missing — set it with `factory.py secrets set` or a scoped env var"
        if item["name"] == "MYAPP_RELEASE_STORE_FILE" and value:
            keystore = Path(value)
            if not keystore.is_absolute() or not keystore.is_file():
                status, detail = R.FAIL, "Keystore path must be an existing absolute file"
            elif is_within(keystore, app.root):
                status, detail = R.FAIL, "Keystore is inside the app source tree; move it outside the project"
        rotation = meta.get(item["name"], {}).get("rotated_at")
        age_days = (now - datetime.fromisoformat(rotation)).days if rotation else None
        if value and item["rotation_days"] and age_days is not None and age_days > item["rotation_days"]:
            status = R.WARN if status == R.PASS else status
            detail += f"; last rotated {age_days} days ago (policy {item['rotation_days']})"
        checks.append(R.check(f"Secret {item['name']}", status, detail))
        inventory.append({"name": item["name"], "purpose": item["purpose"], "present": bool(value),
                          "source": source, "age_days": age_days, "rotation_days": item["rotation_days"]})
    if len(checks) == 1:
        checks.append(R.check("Declared secrets", R.NOT_APPLICABLE,
                              f"No secrets declared for {environment} in APP_CONFIG.json"))
    return R.make_report(app, "secrets-validate", f"Secret configuration ({environment})", checks,
                         milestone=41, data={"environment": environment, "inventory": inventory},
                         limitations=["Presence and file-permission checks only; secret validity is not tested "
                                      "against the issuing service."])


def _gitignore_check(app):
    gitignore = app.root / ".gitignore"
    if not gitignore.is_file():
        return R.check(".gitignore secret coverage", R.FAIL, "No root .gitignore")
    text = gitignore.read_text(encoding="utf-8", errors="replace")
    missing = [p for p in GITIGNORE_REQUIRED if p not in text]
    return R.check(".gitignore secret coverage", R.FAIL if missing else R.PASS,
                   f"Missing patterns: {', '.join(missing)}" if missing else "Required patterns present")


def scan_exposure(app: AppContext) -> dict:
    """Scan the app tree for secret-shaped values and signing material. Values are never reported."""
    findings, client_config, signing_files = [], [], []
    scanned = skipped = 0
    for path in iter_files(app.root):
        relative = str(path.relative_to(app.root))
        if any(path.match(pattern) for pattern in SIGNING_FILE_PATTERNS):
            signing_files.append(relative)
            continue
        if path.suffix not in TEXT_SUFFIXES and path.name not in {".env"}:
            continue
        text = read_text(path)
        if text is None:
            skipped += 1
            continue
        scanned += 1
        for kind, line in find_secrets(text):
            if path.name in CLIENT_CONFIG_FILES and kind == "google_api_key":
                client_config.append({"file": relative, "line": line, "kind": kind})
            else:
                findings.append({"file": relative, "line": line, "kind": kind})
        for match in re.finditer(r"String\.fromEnvironment\(\s*['\"]([A-Z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD)"
                                 r"[A-Z0-9_]*)['\"]\s*,\s*defaultValue:\s*['\"]([^'\"]+)['\"]", text):
            findings.append({"file": relative, "line": text.count("\n", 0, match.start()) + 1,
                             "kind": f"dart_define_default:{match.group(1)}"})
    checks = [
        R.check("Secret-shaped values in source", R.FAIL if findings else R.PASS,
                f"{len(findings)} finding(s) in {scanned} files" if findings else f"None in {scanned} files"),
        R.check("Signing material in project tree", R.FAIL if signing_files else R.PASS,
                ", ".join(signing_files) or "None found"),
        _gitignore_check(app),
    ]
    if client_config:
        checks.append(R.check("Client configuration API keys", R.WARN,
                              f"{len(client_config)} Firebase client key(s); restrict them in Google Cloud Console"))
    if skipped:
        checks.append(R.check("Oversized files skipped", R.WARN, f"{skipped} file(s) over 2 MB not scanned"))
    return R.make_report(app, "secrets-scan", "Secret exposure scan", checks, milestone=41,
                         data={"findings": findings, "client_config_keys": client_config,
                               "signing_files": signing_files, "files_scanned": scanned},
                         limitations=["Pattern-based; cannot detect every secret format.",
                                      "Git history is not scanned (no repository or not requested)."])


def ci_template(app: AppContext, environment: str) -> str:
    """GitHub Actions snippet mapping CI secrets to build environment variables (names only)."""
    names = [item["name"] for item in required_secrets(app, environment)]
    lines = [f"# CI secret mapping for {app.app_id} ({environment}). Values live in the CI secret store.",
             "# Add each with: gh secret set <NAME> --env " + environment, "env:", "  CI: \"true\""]
    for name in names:
        lines.append(f"  {name}: ${{{{ secrets.{name} }}}}")
    if "MYAPP_RELEASE_STORE_FILE" in names:
        lines.append("  # Decode the keystore from a base64 CI secret into $RUNNER_TEMP, never into the repo.")
        lines.append("  MYAPP_RELEASE_SIGNING_ENABLED: \"true\"")
    return "\n".join(lines) + "\n"


ROTATION_GUIDANCE = """Secret rotation guidance
1. Create the new credential in the issuing service (keep the old one active).
2. Store it: python3 scripts/factory.py secrets set --app <id> --env <env> --name <NAME>
   (and update the CI secret of the same name).
3. Run: python3 scripts/factory.py secrets validate --app <id> --env <env>
4. Build and smoke-test with the new value.
5. Revoke the old credential in the issuing service.
6. Upload/signing keys: Play App Signing upload keys are reset through Play Console
   support; never rotate the app signing key yourself.
"""
