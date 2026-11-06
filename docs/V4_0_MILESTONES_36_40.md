# V4.0 Batch 1 — Android scaffolding and app foundations

This batch covers milestones 36–40 only. It extends the existing creator and
configuration workflow; it does not replace the Nova UI source or claim release
readiness.

| Milestone | Capability | Evidence and limits |
|---|---|---|
| 36 | Flutter-generated Android project scaffolding | `scripts/create_app.py` invokes the installed Flutter SDK in an isolated temporary workspace, patches package/namespace/MainActivity identity, and copies only Android platform files. Existing targets are refused; signing and local SDK files are not copied. Flutter APK validation is required for each generated app. |
| 37 | App branding and store asset inventory | The requested app name and primary color are applied to the generated Nova UI app theme. Store inventory is explicit about artwork and screenshots that remain missing; no artwork is fabricated. |
| 38 | Android environment flavors and runtime config | Development, staging and production flavors are generated. Development/staging have distinct application ID suffixes; production retains the requested application ID. Pass a matching `--dart-define=APP_ENV=<environment>` when building/running. Supply API values using `--dart-define`; do not put secrets in client builds. |
| 39 | Versioned app configuration and migration | APP_CONFIG v2 adds branding, environments, Android build, store, privacy, permissions, feature flags and release fields while retaining v1-required fields. `validate_app_config.py --migrate-to-v2 --output <new-file>` performs an additive copy, preserves source data and refuses an existing output. |
| 40 | Static architecture boundary audit | `scripts/architecture_audit.py <flutter-project>` checks Dart import boundaries for recognized feature layers. `PARTIAL` means no recognized layer source files were found; it is not evidence that the architecture is correct. |

## App creation

```bash
python3 scripts/create_app.py \
  --name "Factory Test" \
  --package com.dev.factorytest \
  --target /tmp/factory-test \
  --dry-run
python3 scripts/create_app.py \
  --name "Factory Test" \
  --package com.dev.factorytest \
  --target /tmp/factory-test
cd /tmp/factory-test
flutter pub get
flutter analyze
flutter test
flutter build apk --debug --flavor development \
  --dart-define=APP_ENV=development
```

The command never overwrites the target. It does not configure release signing,
Firebase, AdMob, store assets, production credentials or deploy an app. If
scaffolding fails, the target is not published; the temporary staging directory
is cleaned automatically. Flutter scaffolding runs a local SDK command using an
argument list, not a shell command string.

## Configuration migration

Migration is deliberately output-only:

```bash
python3 scripts/validate_app_config.py APP_CONFIG.json \
  --migrate-to-v2 --output APP_CONFIG.v2.json
```

Review the generated file and replace placeholders using verified values.
Never commit credentials in APP_CONFIG, Dart defines, or generated client code.

## Validation scope

Static Python tests verify identity rewriting, flavor configuration, safe
migration, and import-boundary rules. They do not prove that every target app
builds, that a flavor is installed on a device, that store artwork is complete,
or that production signing/release gates have passed. Those require app-specific
Flutter and human review.
