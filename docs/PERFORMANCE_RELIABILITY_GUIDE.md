# Performance and reliability guide

- Profile before optimizing; do not claim performance gains without measurement.
- Use lazy builders for long lists and grids.
- Cache images where appropriate and provide placeholders/error fallbacks.
- Avoid expensive work in `build()`; keep rebuild scopes small.
- Dispose controllers, focus nodes, animation controllers and subscriptions.
- Cancel or ignore stale async results when screens are disposed.
- Use timeouts and actionable error handling for network operations.
- Avoid blocking the UI isolate with large parsing or CPU-heavy work.
- Test low-memory and slow-network behavior where relevant.
- Measure startup and frame performance in profile/release modes on representative devices.
- Review large text, contrast, TalkBack semantics, focus order and reduced-motion behavior.
- Do not add caching, isolates or complex optimization until requirements or profiling justify them.
