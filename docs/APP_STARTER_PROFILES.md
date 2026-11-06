# App starter profiles

Select one profile during planning. Profiles are guidance, not rigid templates. Combine them only when the product truly needs it.

## 1. Offline utility
Examples: calculators, body measurements, simple trackers.
- Local storage selected to match query and migration needs.
- No account or backend unless required.
- Export/backup and clear-data behavior considered.
- Offline-first UI, empty states and local data tests.

## 2. Productivity
Examples: tasks, notes, habit trackers.
- Local-first data model and reminder/notification choice.
- Search, filters, sorting and settings patterns.
- Data export and schema migration strategy.
- Optional account/sync only when justified.

## 3. Fitness or wellness tracker
- User-entered metrics and history charts.
- Clear units, date ranges and empty-history states.
- Privacy-first storage and data deletion.
- Avoid medical claims unless appropriately supported.

## 4. Content app
Examples: articles, devotional content, educational material.
- Browse/search/detail/favorites/settings screens.
- Cache and offline reading behavior if needed.
- Content source, licensing and update mechanism clarified.
- Notifications only if requested.

## 5. API-driven app
- Typed API models and repository/service boundary.
- Loading, timeout, retry, unauthorized and server-error handling.
- Pagination/search/filter patterns where relevant.
- Never embed server secrets in the mobile client.

## 6. Authentication-backed app
- Ask which authentication methods are required.
- Handle loading, invalid input, expired session, sign-out and account deletion.
- Apply authorization rules on the backend, not only in UI.
- Add Firebase only if selected; do not assume Firebase by default.

## 7. Commerce or booking app
- Clarify catalog, cart/booking, pricing, cancellation and payment scope.
- Treat payment providers and server-side verification as separate integrations.
- Do not store sensitive payment data in the app.
- Add confirmation, failure, retry and history states.

## 8. Community or social app
- Clarify profiles, content moderation, report/block, privacy and notification needs.
- Design abuse/reporting paths and deletion controls before coding.
- Add real-time backend only when required.

## Profile selection output
Claude should state: selected profile, required modules, optional modules, storage/backend decision, excluded modules and why.
