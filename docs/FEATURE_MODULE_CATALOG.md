# Optional feature module catalog

Select modules based on the app's confirmed requirements; do not include every module by default.

| Module | Include when | Key checks |
|---|---|---|
| Local storage | Data must persist on device | Schema changes, clear/export data |
| API client | App uses a remote service | Timeouts, errors, secret handling |
| Firebase Auth | Firebase auth explicitly selected | Sign-in/out, session expiry |
| Firestore / Realtime DB | Selected data service requires it | Security rules, offline behavior |
| Firebase Storage | User/media file storage needed | File size/type, access rules |
| Push notifications | User benefits from alerts | Permission, opt-in, deep links |
| AdMob | Monetization explicitly selected | Test units, consent, placement |
| Analytics | Product measurement requested | Data minimization and consent |
| Crash reporting | Crash diagnostics requested | PII filtering, environment separation |
| Localization | Multiple languages required | ARB files, text expansion |
| Export / backup | User data should be portable | Format, restore validation |
| Sync | Data shared across devices | Conflicts, retries, auth boundaries |
| In-app purchases | Paid digital features needed | Store billing, server verification |
| Deep links | Links should open app destinations | Validation, fallback behavior |

For every chosen module, record status as `not configured`, `configured`, `tested`, or `not applicable`. Never mark an integration tested solely because source code was generated.
