# MyAppFactory workflow

1. Define the app and target users; agree on screens and user journeys before implementation.
2. Attach UI reference images and use `prompts/master_app_prompt.md` in Claude Code.
3. Answer Firebase and AdMob setup questions in `prompts/firebase_admob_setup.md`; either can remain disabled.
4. Duplicate `templates/nova_ui_flutter_starter/` into `apps/<app_name>/`.
5. Have Claude implement the app feature-by-feature, reusing Nova UI components.
6. After each major feature, inspect the diff and run formatting, analysis and focused tests.
7. Before release, follow `docs/QUALITY_CHECKLIST.md` and review the changelog.
8. Never commit real credentials, service config secrets, signing keys or production ad IDs into a public repository.

## AI change-protection rules
- Inspect before editing; do not replace project files wholesale without explaining why.
- Preserve existing architecture, routes, models, local data and business rules.
- Make small, reviewable changes and list every file changed.
- Do not report a command as passed unless its actual output confirms success.
