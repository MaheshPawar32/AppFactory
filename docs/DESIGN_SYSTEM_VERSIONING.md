# Design-system versioning and template sync

## Source of truth
`design_system/nova_ui_flutter/` is the canonical Nova UI source. `templates/nova_ui_flutter_starter/` should mirror its approved starter files.

## Change process
1. Make and test a change in the canonical design system.
2. Update examples/showcase and tests.
3. Document public API changes in the changelog.
4. Sync the approved source to the starter template.
5. Check that the starter has the same component files and core configuration.
6. Run formatting, analysis and tests on both projects when Flutter is available.
7. Record checks actually performed.

## Compatibility
- Avoid silently changing public defaults.
- Document breaking changes and migration instructions.
- Prefer additive APIs where possible.
- Each generated app is a snapshot; do not overwrite app-specific changes during sync.
- A sync script should be reviewed before running and must not delete user files unexpectedly.
