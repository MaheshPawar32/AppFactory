# MyAppFactory V4.0 → V7.0 Implementation Plan

Created: 2026-11-01 (Phase 0). Living document — updated at the end of each batch.

## Phase 0 — verified current state (fresh checks, 2026-11-01)

| Check | Result |
|---|---|
| Python unit tests (`python3 -m unittest discover -s tests`) | PASS — 90 tests |
| Consolidated factory checks (`scripts/run_factory_checks.py`) | PASS — 10/10 |
| Toolchain | Flutter 3.44.4, Python 3.14.6, adb present, `emulator-5554` attached |
| Git | No repository — no history, diff or rollback; backups are file copies under `backups/` |
| Registered apps | `apps/PROJECT_REGISTRY.csv` holds a header only — zero real apps |

| Milestones | Status found | Evidence |
|---|---|---|
| 36, 38, 39 | PASS (prior) | `create_app.py`, `validate_app_config.py`; tests present and passing |
| 37, 40 | PARTIAL (prior) | Store artwork absent; architecture audit finds no layer files in starter |
| 41–44 | NOT IMPLEMENTED | No source or tests |
| 45–49 | PARTIAL | `scripts/quality_qa_engine.py` + 11 tests; device matrix, runtime metrics, vuln scan not exercised |
| 50 | PARTIAL | Signing guard in Gradle (Batch 2) + `flutter_build_engine.py` + `release_artifact_manager.py`; no version management, AAB integrity or ID/namespace validation engine |
| 51–55 | NOT IMPLEMENTED | Only checklists/docs and a read-only release dashboard |
| 56–85 | NOT IMPLEMENTED | No AI provider layer, agents, orchestrator or V5/V7 services |
| V6 | PARTIAL | CSV registry, static HTML control center, batch builds; no per-app state store or interactive UI |

Defects carried forward: `milestone_15…35.py` are 7-line stubs over one generic engine (V3.5 scope, not re-audited here).

## Architecture decisions (defaults — documented, reversible)

1. **One shared core package, `scripts/myappfactory/`.** Every new milestone module uses it for:
   - `context.py` — registered app resolution, path containment (`AppContext.resolve()` rejects any path outside the app root), and a per-app state directory `state/apps/<app_id>/`. This is the isolation boundary for V6.
   - `approvals.py` — single-use, payload-hash-bound, expiring human approvals. Requests are created by tools; approval requires a separate explicit `approve` command. Tools never self-approve.
   - `audit.py` — append-only, hash-chained audit log per app plus a factory log.
   - `redact.py` / `secrets.py` — secret detection and redaction used by every log and report writer.
   - `runner.py` — allowlisted executables, argument arrays only, timeouts, cancellation, redacted logs.
   - `reports.py` — status vocabulary (PASS, FAIL, PARTIAL, NOT IMPLEMENTED, NOT RUN, NEEDS MANUAL VERIFICATION), app identity stamped on every report, refuse-overwrite writes.
2. **One CLI entry point, `scripts/factory.py <group> <command>`,** instead of one script per milestone. Existing scripts stay and are reused, not duplicated (e.g. the release engine calls `flutter_build_engine.py`; QA certification reads `quality_qa_engine.py` output).
3. **AI is provider-independent.** `myappfactory/ai/` has a provider interface with `anthropic` (HTTP via stdlib, key from env/secret store only), `mock` (tests only, always labelled MOCK) and `none` adapters. With no credentials configured, AI features run their deterministic local analysis and report the external integration as NOT RUN / NEEDS MANUAL CONFIGURATION.
4. **Control Center UI = local Python stdlib web app** (`scripts/control_center_server.py`) bound to `127.0.0.1`, per-launch session token, CSRF-protected POSTs, no new dependencies. It extends the existing Python-generated HTML dashboards instead of adding an unrelated stack. Every button maps to a real core command; approval-gated actions show the approval request rather than executing.
5. **Per-app state lives in the factory, not in the app source**, under `state/apps/<app_id>/` (git-ignored), so reports, history and approvals never leak into app repos or other apps.

## Execution batches

| Batch | Milestones | Scope |
|---|---|---|
| 3 | core + 41–44 | Shared core; secrets; auth QA; data/offline/backup; privacy inventory |
| 4 | 45–49 | Integrate `quality_qa_engine` with the core (per-app history, isolation); close evidence gaps that can be closed locally |
| 5 | 50–55 | Release engine, pipeline, Play compliance, Play Console (manual workflow + API architecture), monitoring/rollback, certification |
| 6 | 56–65 | AI provider layer; product analyst; UI generator; code review; bug detection; test generator; visual regression; backend; API contracts; DB migrations; localization (en/mr/hi) |
| 7 | 66–75 | Updates; feature flags; monetization QA; analytics; costs; support; crash-to-fix; portfolio; maintenance planner; factory health |
| 8 | V6 | Registry v2, per-app dashboards, build queue, cross-app isolation tests, Control Center UI |
| 9 | 76–85 | Orchestrator; agents with scoped permissions; codebase understanding; self-healing; quality intelligence; product improvement; release decision; cross-app knowledge; scheduler; self-optimization |
| 10 | Audit | Fresh independent verification of 36–85; final reports (MD + JSON) |

After each batch: back up touched files, run Python tests + compile + factory checks, run Flutter analyze/test/build where Flutter-facing code changed, write the batch section of the version report.

## Honest limits known up front

- External services (Play Console API, Crashlytics, Supabase/Firebase projects, AI provider keys, AdMob/Billing) have no credentials in this workspace. Their adapters will be built and tested against local fixtures; live integration will be reported NOT RUN until you configure them.
- Device coverage is limited to the attached emulator(s).
- No milestone becomes PASS from documentation; each needs source + tests exercising real behaviour.
