# Multi-app project registry

Maintain `apps/PROJECT_REGISTRY.csv` with one row per app. Keep status factual and update it after actual checks.

Suggested fields:
- app_name
- package_name
- app_version
- profile
- state_management
- storage
- backend
- firebase_services
- admob_status
- languages
- current_stage
- last_analyzer_status
- last_test_status
- last_build_status
- last_verified_at
- known_issues
- next_action

Statuses should use values such as `not_started`, `in_progress`, `passed`, `failed`, `not_run`, `not_configured`, and `not_applicable`. Never mark a test or build as passed from source inspection alone.


## v1.7 workflow

Create new app folders with `scripts/create_app.py` after a dry run. Use the acceptance criteria and release verification templates for evidence. Record only observed analyzer/test/build results in the registry; use `NOT RUN` when a check has not executed. Dependency audit findings are advisory and do not equal a security certification.
