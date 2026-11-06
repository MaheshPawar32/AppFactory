# Offline and Failure-State Testing

For each critical journey, verify loading, success, empty, offline, timeout, server error, invalid input, denied permission, expired session and retry behavior where applicable.

- Simulate airplane mode or disable network access on a test device.
- Confirm cached/offline data behavior matches the app's requirements.
- Ensure retries are bounded and users can recover without duplicate submissions.
- Confirm local writes survive app restart when persistence is promised.
- Test API errors and malformed responses without exposing secrets or stack traces.
- For financial, destructive or externally visible actions, avoid blind retries; use idempotency or confirmation where appropriate.
- Record device, steps, expected/actual behavior and evidence in the app's test report.
