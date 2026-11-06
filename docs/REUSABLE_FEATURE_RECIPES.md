# Reusable Feature Recipes

Before adding a recipe, inspect the app's architecture and existing dependencies. Recipes are implementation guides, not permission to add every feature to every app.

| Recipe | Include when needed | Minimum states / checks |
|---|---|---|
| Onboarding | First-run explanation or setup | Skip/resume, persisted completion, accessibility |
| Settings | User-controlled preferences | Defaults, persistence, reset confirmation |
| Local storage | Offline-first or private local data | Migration, corruption/recovery, clear-data behavior |
| Notifications | Reminders or timely updates | Permission denied, schedule changes, time zone |
| Analytics | Product measurement explicitly approved | Consent/privacy review, no sensitive payloads |
| Import/export | User needs data portability | Validation, cancellation, malformed files |
| Search/filter | Meaningful local or remote collections | Empty results, clear filters, loading/error |
| Background work | Work must continue outside the screen | OS limits, retries, duplicate prevention, battery |
| Authentication | Account-based features require identity | Loading, expired session, logout and data isolation |

For new Flutter projects, Provider is the default unless the brief says otherwise. For existing projects, preserve the current state management and architecture.
