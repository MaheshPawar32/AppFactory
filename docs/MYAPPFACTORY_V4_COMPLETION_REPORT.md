# MyAppFactory V4.0 Completion Report

Living report — one section per batch. Statuses follow the master prompt: PASS only with source + tests exercising behaviour.

## Batch 3 — Shared core + milestones 41–44 (2026-11-01)

### Shared core (`scripts/myappfactory/`)

| Module | Purpose | Tests |
|---|---|---|
| `context.py` | Registered-app resolution; symlink-safe path containment; per-app state dir `state/apps/<app_id>/`; duplicate/overlapping registry roots rejected | `ContextIsolationTests` (3) |
| `approvals.py` | Payload-hash-bound, single-use, expiring human approvals; named human approver required; per-app scope | `AuditAndApprovalTests` (4) |
| `audit.py` | Append-only hash-chained audit log with redaction | tamper detection test |
| `redact.py` | Secret patterns, sensitive env values, sensitive key names | `RedactionTests` (3) |
| `runner.py` | Allowlisted executables, argument arrays only, timeout, cancellation, redacted output; missing tool → NOT RUN | `RunnerAndReportTests` (3) |
| `reports.py` | Status vocabulary, roll-up, app identity on every report, refuse-overwrite, cross-app write refusal | `RunnerAndReportTests` |
| `project.py` | Pubspec/lock/manifest/config readers (no YAML or XML-parser dependency) | via milestone tests |
| `cli.py`, `scripts/factory.py` | Single CLI: `approvals`, `audit`, `secrets`, `auth`, `data`, `privacy` | `CliTests` (3) |

### Milestones

| # | Name | Status | Source | Evidence | Limitations / manual |
|---|---|---|---|---|---|
| 41 | Secure Secrets Management | PASS | `secrets_manager.py` | 8 tests: 0700/0600 store outside app tree; values absent from reports/audit; app-scoped lookup (A cannot resolve B's store or scoped env); production requires release-signing secrets; keystore inside project rejected; exposure scan (secrets, signing files, `.gitignore` gaps, `fromEnvironment` defaults, `build/` skipped); CI template names-only; rotation-overdue warning. Real run on Nova UI: scan PASS (45 files); production validate FAIL (signing not configured — true state). | Pattern scanning cannot catch every format; no Git history scan (no repo). Local store is file-permission protected, not encrypted at rest (relies on FileVault). |
| 42 | Authentication & Authorization QA | PARTIAL | `auth_qa.py` | 5 tests: offline app → NOT APPLICABLE; token-in-SharedPreferences, token logging, plain HTTP detected; declared-vs-implemented; scenario test discovery; Supabase adapter verified with a fake transport; live checks NOT RUN without credentials. Real run on Nova UI: NOT APPLICABLE. | Firebase/Supabase live adapters not run against a real project (no test project/credentials). Server-side rules/RLS need manual checks. |
| 43 | Data, Offline & Backup Readiness | PARTIAL | `data_readiness.py` | 7 tests: Hive schema snapshot + unsafe field-index reuse; duplicate typeIds/field ids; sqflite version without `onUpgrade`; SQLite table change without version bump; unguarded network calls; test discovery; device backup/restore/offline workflows enforce package isolation; restore needs approval; offline simulation always restores connectivity even on failure. | Device backup/restore and offline launch not yet exercised on the emulator (scheduled for Batch 4 device run). Supabase/Firebase remote backups are manual. |
| 44 | Privacy & Data Protection | PASS | `privacy.py` | 4 tests: permission + SDK inventory; inferred vs declared categories; policy URL / deletion / consent / retention checks; DRAFT Data Safety mapping; sign-off approval bound to the exact draft — invalidated when a new data SDK appears; `tools:node="remove"` honoured. Real run on Nova UI: PARTIAL (no policy URL, retention undefined, sign-off pending — expected). | Not legal advice. SDK categories are typical defaults; Play policy must be checked against current Google documentation at submission. |

### Commands and results

| Command | Result |
|---|---|
| `python3 -m unittest discover -s tests` | PASS — 131 tests (90 existing + 41 new) |
| `python3 -m compileall -q scripts tests` | PASS |
| `python3 scripts/run_factory_checks.py` | PASS — 10/10 |
| `factory.py secrets scan / auth / data / privacy --project design_system/nova_ui_flutter` | Ran; results above; audit log verified intact |

### Environment finding

Homebrew Python 3.14.6 on this Mac has a broken `pyexpat` (links against an older `/usr/lib/libexpat.1.dylib`; `import pyexpat` fails). Any Python XML parsing crashes. The new tools avoid it; existing scripts that parse XML may fail. Fix: `brew reinstall python@3.14 expat`.

### Backups

`backups/batch3_2026-11-01/` — `run_factory_checks.py`, `release_preflight.py`, `.gitignore` (only `.gitignore` was modified: `state/` and `backups/` added).
