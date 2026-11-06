# MyAppFactory V4–V7 Execution Journal

Resume rule: read this file, then re-run `python3 -m unittest discover -s tests` and
`python3 scripts/run_factory_checks.py`. A journal entry is a pointer, not evidence —
the per-milestone evidence lives in the version completion reports and in tests.

## Standing decisions

| Decision | Choice | Why |
|---|---|---|
| Shared core | `scripts/myappfactory/` (Batch 3) | One place for isolation, approvals, audit, redaction |
| CLI | `scripts/factory.py <group>`; groups register via `@cli.group`, imported in `extensions.py` | No per-milestone script sprawl |
| Per-app state | `state/apps/<app_id>/` (git-ignored) | Isolation; nothing written into app repos unless approved |
| AI providers | `claude-code` (headless `claude -p`, code-writing default), `anthropic` (HTTP API), `mock` (tests only, labelled MOCK), `none` | User already uses Claude Code; mock never reported as real |
| External AI calls | Gated by `external_ai_call` approval unless the app opts in via factory settings | Project context leaves the machine |
| Control Center | Local stdlib web server on 127.0.0.1, session token + CSRF | Reuses Python/HTML stack; no new dependencies |
| XML | No `xml.etree` in new code (`pyexpat` broken on this Mac) | Environment defect |

## Checkpoints

### CP-0 — 2026-11-01 Phase 0
- Verified: 90 Python tests PASS; factory checks 10/10 PASS; emulator-5554 available; no git repo.
- Plan: `docs/MYAPPFACTORY_V7_IMPLEMENTATION_PLAN.md`.

### CP-1 — 2026-11-01 Batch 3 (core + 41–44)
- Files: `scripts/myappfactory/{__init__,context,approvals,audit,redact,runner,reports,project,secrets_manager,auth_qa,data_readiness,privacy,cli,extensions}.py`, `scripts/factory.py`, `tests/factory_fixtures.py`, `tests/test_v4_batch3.py`; `.gitignore` (+`state/`, `backups/`).
- Results: 131 tests PASS; compileall PASS; factory checks 10/10 PASS.
- Status: 41 PASS, 42 PARTIAL, 43 PARTIAL, 44 PASS.

### CP-2 — 2026-11-01 Phase 1 closure + AI layer
- Sample app `com.dev.factorysample` (session scratchpad): create PASS, analyze no issues, test 2/2, debug APK built.
- M43 on emulator-5554: offline launch (airplane mode) — launched, no crash, alive, connectivity restored; device backup tar written to state; restore refused pending approval `apr_22f4cfb20508` (left for the user).
- Fixed: runner reported a missing cwd as "tool not found"; now `CommandRejected`; device workflows create the state dir.
- AI layer: `scripts/myappfactory/ai/{providers,service,schema}.py`, `cli_ai.py`; tests `tests/test_ai_layer.py`.
- Results: 148 tests PASS.

### CP-3 — in progress: Phase 2 (45–49)
