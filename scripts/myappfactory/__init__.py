"""Shared core for MyAppFactory V4–V7 tools.

Every milestone module builds on these primitives so that isolation, approvals,
redaction, auditing and report status rules are enforced in one place:

- context:   registered-app resolution, path containment, per-app state dirs
- approvals: single-use, payload-bound, expiring human approvals
- audit:     append-only hash-chained audit logs
- redact:    secret detection and redaction for logs and reports
- runner:    allowlisted, argument-array command execution with timeouts
- reports:   status vocabulary and refuse-overwrite report writing
"""

__version__ = "7.0.0-dev"
