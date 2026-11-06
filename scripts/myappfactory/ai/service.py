"""AI service: provider selection, consent, context filtering, retries, validation, usage ledger.

External providers receive project context only when the app has a standing
consent recorded by a named human (`factory.py ai consent --grant --by NAME`).
Without consent, configuration or credentials, callers get ProviderNotConfigured
and must fall back to local deterministic analysis, reported as kind=local.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from ..audit import app_audit
from ..context import AppContext
from ..project import iter_files, read_text
from ..redact import redact
from . import schema as S
from .providers import (EXTERNAL, MOCK, AIRequest, AIResponse, Provider, ProviderError,
                        ProviderNotConfigured, make_provider)

DEFAULT_CONFIG = {"provider": "none", "model": None, "max_retries": 2, "min_interval_seconds": 1.0,
                  "max_context_chars": 120_000, "monthly_budget_usd": 25.0}
# Never sent to a provider, even with consent.
EXCLUDED_NAMES = {".env", "key.properties", "google-services.json", "GoogleService-Info.plist", "local.properties"}
EXCLUDED_SUFFIXES = {".jks", ".keystore", ".p12", ".pem", ".p8", ".key", ".png", ".jpg", ".jpeg", ".webp",
                     ".gif", ".ttf", ".otf", ".apk", ".aab", ".so", ".jar", ".lock"}
_rate_lock = threading.Lock()
_last_call: dict[str, float] = {}


def config_path(state_root: Path) -> Path:
    return Path(state_root) / "factory" / "ai_config.json"


def load_config(state_root: Path) -> dict:
    path = config_path(state_root)
    data = dict(DEFAULT_CONFIG)
    if path.is_file():
        data.update(json.loads(path.read_text(encoding="utf-8")))
    return data


def save_config(state_root: Path, **changes) -> dict:
    data = load_config(state_root)
    for key, value in changes.items():
        if key not in DEFAULT_CONFIG:
            raise ValueError(f"Unknown AI setting: {key}")
        data[key] = value
    if data["provider"] not in ("none", "anthropic", "claude-code", "mock"):
        raise ValueError("provider must be none, anthropic, claude-code or mock")
    path = config_path(state_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


# --- consent --------------------------------------------------------------------

def _consent_file(app):
    return app.state_path("ai", "consent.json")


def consent(app: AppContext) -> dict | None:
    path = _consent_file(app)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def set_consent(app: AppContext, granted: bool, by: str, note="") -> dict:
    by = (by or "").strip()
    if not by or by.lower() in {"factory", "ai", "agent", "system", "auto"}:
        raise PermissionError("Consent must be recorded by a named human")
    path = _consent_file(app)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"granted": granted, "by": by, "at": datetime.now(timezone.utc).isoformat(), "note": note}
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    app_audit(app).append("ai_consent_" + ("granted" if granted else "revoked"), by, {"note": note}, app.app_id)
    return record


# --- context --------------------------------------------------------------------

def collect_context(app: AppContext, paths=None, max_chars=DEFAULT_CONFIG["max_context_chars"],
                    subdirs=("lib", "test")) -> tuple[str, list[str]]:
    """Gather redacted source text from inside the app only. Returns (text, included_files)."""
    chosen = []
    if paths:
        for relative in paths:
            chosen.append(app.resolve(relative))  # IsolationError for anything outside the app
    else:
        for sub in subdirs:
            chosen += list(iter_files(app.root, {".dart", ".yaml", ".json", ".md", ".arb"}, sub))
        for name in ("pubspec.yaml", "APP_CONFIG.json", "README.md"):
            if (app.root / name).is_file():
                chosen.append(app.root / name)
    parts, included, used = [], [], 0
    for path in chosen:
        if path.name in EXCLUDED_NAMES or path.suffix in EXCLUDED_SUFFIXES or not path.is_file():
            continue
        text = read_text(path)
        if text is None:
            continue
        relative = str(path.relative_to(app.root))
        block = f"\n=== {relative} ===\n{redact(text)}"
        if used + len(block) > max_chars:
            parts.append(f"\n=== [context limit reached; {len(chosen) - len(included)} file(s) omitted] ===")
            break
        parts.append(block)
        included.append(relative)
        used += len(block)
    return "".join(parts), included


# --- service --------------------------------------------------------------------

class AIService:
    def __init__(self, app: AppContext, provider: Provider | None = None, config: dict | None = None,
                 sleep=time.sleep):
        self.app = app
        self.config = config or load_config(app.state_root)
        self.provider = provider or make_provider(self.config["provider"], self.config.get("model"))
        self.sleep = sleep

    def status(self) -> dict:
        ok, reason = self.provider.available()
        record = consent(self.app)
        needs_consent = self.provider.kind == EXTERNAL
        consented = bool(record and record.get("granted"))
        if self.provider.kind == MOCK:
            label = "MOCK (tests only)"
        elif not ok:
            label = "NEEDS MANUAL CONFIGURATION"
        elif needs_consent and not consented:
            label = "CONFIGURED — app consent missing"
        else:
            label = "CONNECTED"
        return {"provider": self.provider.name, "kind": self.provider.kind, "available": ok, "reason": reason,
                "consent": record, "status": label, "spent_this_month_usd": self.month_spend()}

    def ready(self) -> bool:
        return self.status()["status"] in ("CONNECTED", "MOCK (tests only)")

    def _ledger(self):
        return self.app.state_path("ai", "usage.jsonl")

    def month_spend(self) -> float:
        path = self._ledger()
        if not path.is_file():
            return 0.0
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        total = 0.0
        for line in path.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            if entry["at"].startswith(month) and entry.get("cost_usd") and entry.get("kind") == EXTERNAL:
                total += entry["cost_usd"]
        return round(total, 4)

    def usage(self) -> list[dict]:
        path = self._ledger()
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()] if path.is_file() else []

    def _record(self, request: AIRequest, response: AIResponse | None, error: str | None):
        entry = {"at": datetime.now(timezone.utc).isoformat(), "app_id": self.app.app_id, "task": request.task,
                 "provider": self.provider.name, "kind": self.provider.kind, "error": error,
                 **(response.to_dict() if response else {})}
        path = self._ledger()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def _rate_limit(self):
        interval = float(self.config.get("min_interval_seconds", 0) or 0)
        with _rate_lock:
            wait = _last_call.get(self.provider.name, 0) + interval - time.time()
            if wait > 0:
                self.sleep(wait)
            _last_call[self.provider.name] = time.time()

    def complete(self, request: AIRequest) -> AIResponse:
        state = self.status()
        if not state["available"]:
            raise ProviderNotConfigured(state["reason"])
        if self.provider.kind == EXTERNAL and not (state["consent"] or {}).get("granted"):
            raise ProviderNotConfigured(f"External AI not consented for {self.app.app_id}; "
                                        "run `factory.py ai consent --grant --by <name>`")
        if self.provider.kind == EXTERNAL and state["spent_this_month_usd"] >= float(self.config["monthly_budget_usd"]):
            raise ProviderNotConfigured(f"Monthly AI budget reached ({self.config['monthly_budget_usd']} USD)")
        if request.schema:
            request.schema = S.strict(request.schema)
        attempts = int(self.config.get("max_retries", 2)) + 1
        last_error = None
        for attempt in range(attempts):
            self._rate_limit()
            try:
                response = self.provider.complete(request)
            except ProviderNotConfigured:
                raise
            except ProviderError as exc:
                last_error = exc
                self._record(request, None, str(exc))
                if exc.retryable and attempt + 1 < attempts:
                    self.sleep(min(2 ** attempt, 30))
                    continue
                raise
            if request.schema:
                try:
                    data = response.data if response.data is not None else json.loads(response.text)
                except json.JSONDecodeError:
                    data, problems = None, ["Response is not valid JSON"]
                else:
                    problems = S.validate(data, request.schema)
                if problems:
                    last_error = ProviderError("Structured output invalid: " + "; ".join(problems[:5]))
                    self._record(request, response, str(last_error))
                    if attempt + 1 < attempts:
                        continue
                    raise last_error
                response.data = data
            self._record(request, response, None)
            app_audit(self.app).append("ai_call", f"ai:{self.provider.name}",
                                       {"task": request.task, "kind": response.kind, "model": response.model},
                                       self.app.app_id)
            return response
        raise last_error or ProviderError("AI call failed")


def run_ai_or_local(app: AppContext, request: AIRequest, local_fn, service: AIService | None = None) -> dict:
    """Try the configured provider; otherwise run deterministic local analysis. Always labelled."""
    service = service or AIService(app)
    try:
        response = service.complete(request)
        return {"source": response.kind, "provider": response.provider, "model": response.model,
                "data": response.data if response.data is not None else response.text,
                "usage": response.usage, "cost_usd": response.cost_usd, "cost_basis": response.cost_basis}
    except ProviderNotConfigured as exc:
        return {"source": "local", "provider": "factory-deterministic", "model": None,
                "data": local_fn(), "ai_unavailable_reason": str(exc)}
    except ProviderError as exc:
        return {"source": "local", "provider": "factory-deterministic", "model": None,
                "data": local_fn(), "ai_error": str(exc)}
