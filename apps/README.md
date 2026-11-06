# Apps workspace

Create one folder per app: `apps/<app_name>/`.

Use `PROJECT_REGISTRY.csv` to track project decisions and actual verification status. Do not put credentials, signing keys or production service configuration in the registry. See `docs/STANDARD_DELIVERABLES.md` for the expected documentation for each app.


## Create a project safely

From the MyAppFactory root, run `python3 scripts/create_app.py --name "My App" --package com.dev.myapp --target apps/myapp --dry-run`, then rerun without `--dry-run`. The script refuses to overwrite an existing target. It copies only the starter and metadata; Android platform setup and package/applicationId wiring must be completed and verified separately.
