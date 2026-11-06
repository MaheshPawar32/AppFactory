# MyAppFactory v2.2 — Consistency, Testing and Visual Evidence

## What changed
- `APP_CONFIG.json` provides a machine-readable single source of truth alongside the existing YAML template.
- `scripts/validate_app_config.py` checks required values, package-name shape and likely placeholders.
- `scripts/validate_project_registry.py` checks registry columns, duplicate app names and status vocabulary.
- `scripts/asset_license_report.py` checks asset/license inventory completeness without making legal conclusions.
- `scripts/screenshot_compare.py` optionally runs ImageMagick's `compare` command. It exits with `NOT RUN` when screenshots are missing or ImageMagick is unavailable.
- `tests/test_factory_tools.py` covers key success/failure paths for the new helpers.
- CI runs the new Python unit tests and smoke checks the new tools.

## Commands
```bash
python3 scripts/validate_app_config.py templates/project_docs/APP_CONFIG.json
python3 scripts/validate_project_registry.py
python3 scripts/asset_license_report.py
python3 -m unittest discover -s tests -v
python3 scripts/screenshot_compare.py reference.png runtime.png --diff diff.png --metric RMSE
```

## Screenshot comparison notes
Install ImageMagick separately if you want image comparison. The script does not install it. `COMPARED` means the command ran and returned a metric; it does not mean the UI passed. Review the generated diff manually and compare only equivalent screen sizes, states, text scale, locale and theme.

## Configuration migration
Existing `APP_CONFIG.yaml` remains unchanged and supported as a human-readable template. The new validator accepts JSON only and does not silently parse YAML. Keep both aligned if you maintain both files; no existing project config is rewritten.

## Verification boundaries
The Python unit tests verify helper behavior, not Flutter app correctness, real device rendering, full security scanning or store compliance.
