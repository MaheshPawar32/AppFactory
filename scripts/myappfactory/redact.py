"""Secret detection and redaction. Values are never returned to callers that report."""
from __future__ import annotations

import os
import re

REDACTED = "[REDACTED]"

# (kind, pattern). Patterns match the secret value itself so it can be replaced.
SECRET_PATTERNS: tuple[tuple[str, re.Pattern], ...] = (
    ("private_key_block", re.compile(
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----[\s\S]*?"
        r"(?:-----END (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----|\Z)")),
    ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("openai_style_key", re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}")),
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z_-]{35}")),
    ("github_token", re.compile(r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,}")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("slack_token", re.compile(r"xox[abposr]-[A-Za-z0-9-]{10,}")),
    ("stripe_key", re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{20,}")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("bearer_token", re.compile(r"(?i)(?<=bearer )[A-Za-z0-9._~+/-]{20,}=*")),
    # Only the named group `v` is replaced, so the key name stays readable.
    ("assignment", re.compile(
        r"(?i)(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|"
        r"client[_-]?secret|store[_-]?password|key[_-]?password)[\"']?\s{0,3}[:=]\s{0,3}[\"']"
        r"(?P<v>[^\"'\s$]{6,})(?=[\"'])")),
)


def _replace(pattern: re.Pattern, text: str) -> str:
    if "v" not in pattern.groupindex:
        return pattern.sub(REDACTED, text)
    return pattern.sub(lambda m: m.group(0)[:m.start("v") - m.start()] + REDACTED
                       + m.group(0)[m.end("v") - m.start():], text)

SENSITIVE_ENV_NAME = re.compile(r"(?i)(KEY|SECRET|TOKEN|PASSWORD|PASSWD|CREDENTIAL|PRIVATE)")
MIN_ENV_VALUE_LENGTH = 6
SENSITIVE_KEY = re.compile(r"(?i)^(password|passwd|secret|api_?key|access_?token|refresh_?token|"
                           r"auth_?token|client_?secret|private_?key|value|credential)s?$")


def sensitive_env_values(environ=None) -> list[str]:
    """Values of environment variables whose names look sensitive."""
    environ = os.environ if environ is None else environ
    return sorted(
        {v for k, v in environ.items() if SENSITIVE_ENV_NAME.search(k) and len(v) >= MIN_ENV_VALUE_LENGTH},
        key=len, reverse=True,
    )


def redact(text: str, extra_values=(), environ=None) -> str:
    """Replace known secret values and secret-shaped tokens with a placeholder."""
    if not text:
        return text
    values = [v for v in extra_values if v and len(v) >= 4]
    values += sensitive_env_values(environ)
    for value in sorted(set(values), key=len, reverse=True):
        text = text.replace(value, REDACTED)
    for _, pattern in SECRET_PATTERNS:
        text = _replace(pattern, text)
    return text


def redact_obj(obj, extra_values=(), environ=None):
    """Recursively redact strings inside JSON-like structures."""
    if isinstance(obj, str):
        return redact(obj, extra_values, environ)
    if isinstance(obj, dict):
        # A string stored under a sensitive key name is a value, whatever it looks like.
        return {k: REDACTED if isinstance(v, str) and v and SENSITIVE_KEY.search(str(k))
                else redact_obj(v, extra_values, environ) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact_obj(v, extra_values, environ) for v in obj]
    return obj


def find_secrets(text: str):
    """Yield (kind, line_number) for secret-shaped matches. Never yields the value."""
    for kind, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            yield kind, text.count("\n", 0, match.start()) + 1
