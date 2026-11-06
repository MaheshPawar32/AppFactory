# Flutter Runtime Kit

This is a small, dependency-free Dart source kit. It is not a complete Flutter application and does not add packages.

## Contents
- `AppResult<T>` / `AppFailure`: explicit success/failure outcomes without throwing expected domain failures through UI code.
- `AsyncState<T>`: idle/loading/data/error states, with optional previous data for refreshes.
- `SafeAction`: prevents a second invocation while an async action is still running.

## Integrate
Copy `lib/` into your app's source tree (for example `lib/core/runtime/`) and update imports. Review names against your existing code before integrating. Keep your existing state management; these primitives work with Provider, `setState`, or other architecture.

## Important limitations
- `SafeAction` is a simple single-isolate guard; it does not provide cancellation, persistence, or cross-process locking.
- `AsyncState` models state only; it does not fetch data or render widgets.
- `AppFailure.message` must be a safe user-facing message. Log diagnostic details separately with appropriate privacy controls.
- The kit does not include a network monitor. Use a connectivity plugin only if needed, and remember connectivity does not prove internet access.
- This folder has not been compiled with Dart/Flutter in this environment. Run formatter, analyzer and focused tests in the target Flutter app.
