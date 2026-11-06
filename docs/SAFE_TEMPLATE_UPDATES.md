# Safe Nova UI Template Updates

1. Run `python3 scripts/template_update_preview.py --show-diff` to inspect the source-to-starter difference.
2. If only the reusable starter template needs refreshing, make a Git commit/backup first.
3. Update `templates/nova_ui_flutter_starter/` from `design_system/nova_ui_flutter/` only as an intentional repository-maintenance operation.
4. Run `python3 scripts/check_template_sync.py` and `python3 scripts/project_audit.py`.
5. Existing app projects under `apps/` are never automatically modified by these scripts. For each app, selectively port reviewed component changes and run its tests.
6. Keep app-specific modifications out of the canonical design-system source unless they are truly reusable.

The preview script is read-only. It does not merge changes or safely infer which app-specific code can be replaced.
