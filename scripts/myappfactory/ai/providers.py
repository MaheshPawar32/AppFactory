"""AI provider adapters: anthropic (official SDK), claude-code (headless CLI), mock, none."""
from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from ..redact import redact
from ..runner import run

DEFAULT_MODEL = "claude-opus-5-5"
# USD per million tokens (input, output); Anthropic first-party list prices, 2026-10.
PRICING = {
    "claude-fable-5-1": (10.0, 50.0), "claude-opus-5-5": (4.0, 20.0), "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50),
}
EXTERNAL, LOCAL, MOCK, NONE = "external", "local", "mock", "none"


class ProviderError(RuntimeError):
    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.retryable = retryable


class ProviderNotConfigured(ProviderError):
    pass


@dataclass
class AIRequest:
    task: str                      # template / purpose id, e.g. "product_analysis"
    prompt: str
    system: str = ""
    schema: dict | None = None     # JSON schema for structured output
    max_tokens: int = 16000
    effort: str = "high"
    workdir: Path | None = None    # read-only working directory for claude-code
    allow_edits: bool = False      # claude-code only, and only inside a sandbox copy
    max_budget_usd: float | None = None


@dataclass
class AIResponse:
    text: str
    provider: str
    kind: str
    model: str
    data: object = None
    usage: dict = field(default_factory=dict)
    cost_usd: float | None = None
    cost_basis: str = "none"       # "reported" | "estimated" | "none"
    duration_seconds: float = 0.0
    stop_reason: str = ""

    def to_dict(self):
        return {"provider": self.provider, "kind": self.kind, "model": self.model, "usage": self.usage,
                "cost_usd": self.cost_usd, "cost_basis": self.cost_basis,
                "duration_seconds": self.duration_seconds, "stop_reason": self.stop_reason}


def estimate_cost(model, input_tokens, output_tokens):
    if model not in PRICING:
        return None
    rate_in, rate_out = PRICING[model]
    return round(input_tokens / 1e6 * rate_in + output_tokens / 1e6 * rate_out, 6)


class Provider:
    name = "base"
    kind = NONE

    def available(self) -> tuple[bool, str]:
        return False, "Not configured"

    def complete(self, request: AIRequest) -> AIResponse:
        raise ProviderNotConfigured("No AI provider configured")


class NoneProvider(Provider):
    name = "none"


class MockProvider(Provider):
    """Scripted responses for tests. Output is always labelled kind=mock."""
    name = "mock"
    kind = MOCK

    def __init__(self, responses=None, handler=None):
        self.responses = list(responses or [])
        self.handler = handler
        self.requests: list[AIRequest] = []

    def available(self):
        return True, "Mock provider (tests only)"

    def complete(self, request):
        self.requests.append(request)
        if self.handler:
            payload = self.handler(request)
        elif self.responses:
            payload = self.responses.pop(0)
        else:
            raise ProviderError("Mock provider has no scripted response")
        if isinstance(payload, Exception):
            raise payload
        text = payload if isinstance(payload, str) else json.dumps(payload)
        return AIResponse(text, self.name, MOCK, "mock-model",
                          usage={"input_tokens": len(request.prompt) // 4, "output_tokens": len(text) // 4})


class AnthropicProvider(Provider):
    """Messages API through the official `anthropic` SDK (optional dependency).

    Credentials are resolved by the SDK (ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN or an
    `ant auth login` profile); the factory never stores or logs them. Server-side refusal
    fallbacks are enabled by default.
    """
    name = "anthropic"
    kind = EXTERNAL

    def __init__(self, model=DEFAULT_MODEL, timeout=600.0, max_retries=2, client=None):
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = client

    def _sdk(self):
        try:
            import anthropic  # noqa: F401
            return anthropic
        except ImportError:
            return None

    def available(self):
        if self._client is not None:
            return True, "Injected client"
        if not self._sdk():
            return False, "Python package 'anthropic' not installed (pip install anthropic)"
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                or os.environ.get("ANTHROPIC_PROFILE") or (Path.home() / ".config" / "anthropic").is_dir()):
            return False, "No Anthropic credentials found (set ANTHROPIC_API_KEY or run `ant auth login`)"
        return True, "SDK installed; credentials resolved by the SDK"

    def client(self):
        if self._client is None:
            anthropic = self._sdk()
            if anthropic is None:
                raise ProviderNotConfigured(self.available()[1])
            self._client = anthropic.Anthropic(timeout=self.timeout, max_retries=self.max_retries)
        return self._client

    def complete(self, request):
        anthropic = self._sdk()
        params = {"model": self.model, "max_tokens": request.max_tokens,
                  "messages": [{"role": "user", "content": request.prompt}],
                  "output_config": {"effort": request.effort},
                  "betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
        if request.system:
            params["system"] = request.system
        if request.schema:
            params["output_config"]["format"] = {"type": "json_schema", "schema": request.schema}
        started = time.time()
        try:
            response = self.client().beta.messages.create(**params)
        except Exception as exc:  # map SDK errors without depending on the SDK at import time
            retryable = anthropic is not None and isinstance(
                exc, (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError))
            raise ProviderError(redact(f"{exc.__class__.__name__}: {exc}"), retryable) from None
        if response.stop_reason == "refusal":
            raise ProviderError("Model declined the request (refusal)")
        text = "".join(block.text for block in response.content if block.type == "text")
        usage = {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens,
                 "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0}
        return AIResponse(text, self.name, EXTERNAL, response.model, usage=usage,
                          cost_usd=estimate_cost(self.model, usage["input_tokens"], usage["output_tokens"]),
                          cost_basis="estimated", duration_seconds=round(time.time() - started, 2),
                          stop_reason=response.stop_reason or "")


class ClaudeCodeProvider(Provider):
    """Headless Claude Code (`claude -p`). Read-only tools by default.

    With allow_edits the caller must pass a sandbox working directory (a copy of the
    app); the factory diffs and applies changes only after human approval.
    """
    name = "claude-code"
    kind = EXTERNAL
    READ_ONLY_TOOLS = "Read,Grep,Glob"
    EDIT_TOOLS = "Read,Grep,Glob,Edit,Write"

    def __init__(self, model=None, timeout=1800, default_budget_usd=2.0, run_fn=run):
        self.model = model
        self.timeout = timeout
        self.default_budget_usd = default_budget_usd
        self.run_fn = run_fn

    def available(self):
        return (True, "claude CLI found") if shutil.which("claude") else (False, "claude CLI not on PATH")

    def complete(self, request):
        if request.workdir is None:
            raise ProviderError("claude-code requires a working directory")
        tools = self.EDIT_TOOLS if request.allow_edits else self.READ_ONLY_TOOLS
        command = ["claude", "-p", request.prompt, "--output-format", "json", "--no-session-persistence",
                   "--allowedTools", tools, "--disallowedTools", "Bash,WebFetch,WebSearch",
                   "--max-budget-usd", str(request.max_budget_usd or self.default_budget_usd)]
        if request.allow_edits:
            command += ["--permission-mode", "acceptEdits"]
        if request.system:
            command += ["--append-system-prompt", request.system]
        if request.schema:
            command += ["--json-schema", json.dumps(request.schema)]
        if self.model:
            command += ["--model", self.model]
        result = self.run_fn(command, request.workdir, timeout=self.timeout,
                             allowed={"claude"})
        if result.not_found:
            raise ProviderNotConfigured("claude CLI not found")
        if result.timed_out or result.cancelled:
            raise ProviderError("claude-code timed out or was cancelled", retryable=False)
        try:
            payload = json.loads(result.stdout.strip().splitlines()[-1]) if result.stdout.strip() else {}
        except (json.JSONDecodeError, IndexError):
            raise ProviderError(f"Unparseable claude-code output (exit {result.returncode})")
        if result.returncode != 0 or payload.get("is_error"):
            raise ProviderError(f"claude-code failed: {str(payload.get('result') or result.stderr)[:300]}")
        usage = payload.get("usage") or {}
        data = payload.get("structured_output")
        text = json.dumps(data) if data is not None else str(payload.get("result", ""))
        return AIResponse(text, self.name, EXTERNAL, self.model or "claude-code-default", data=data,
                          usage={"input_tokens": usage.get("input_tokens", 0),
                                 "output_tokens": usage.get("output_tokens", 0)},
                          cost_usd=payload.get("total_cost_usd"),
                          cost_basis="reported" if payload.get("total_cost_usd") is not None else "none",
                          duration_seconds=result.duration_seconds, stop_reason=str(payload.get("subtype", "")))


def make_provider(name, model=None) -> Provider:
    if name == "anthropic":
        return AnthropicProvider(model or DEFAULT_MODEL)
    if name == "claude-code":
        return ClaudeCodeProvider(model)
    if name == "mock":
        return MockProvider()
    return NoneProvider()
