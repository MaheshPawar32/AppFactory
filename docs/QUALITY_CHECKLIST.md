# App quality checklist

## Before implementation
- [ ] Confirm new vs existing app, app name, package name and architecture.
- [ ] Confirm Firebase services and AdMob formats individually; both are optional.
- [ ] Confirm offline behavior, storage, languages, permissions and data deletion needs.
- [ ] Review supplied UI images and produce a screen inventory before coding.
- [ ] Create a Git checkpoint before feature work.

## UI and accessibility
- [ ] Every screen has loading/empty/error/success/offline states where relevant.
- [ ] Icon-only actions have semantic labels and controls have accessible touch targets.
- [ ] Check large text, contrast, keyboard focus and TalkBack.
- [ ] Check compact and expanded window sizes; no overflow on small Android devices.
- [ ] Use consistent motion and respect reduced-motion preferences.

## Data and reliability
- [ ] Preserve user input after recoverable failures.
- [ ] Prevent duplicate submissions and show progress while saving.
- [ ] Handle timeouts, no network, expired sessions and permission denial.
- [ ] Keep secrets out of source control; include `.env.example` only for placeholders.
- [ ] Add migrations and backup/export guidance when local data schemas change.

## Verification and release
- [ ] `dart format --set-exit-if-changed .`
- [ ] `flutter analyze`
- [ ] `flutter test`
- [ ] `flutter build apk --debug`
- [ ] Review dependencies and licenses.
- [ ] Verify app icon, package ID, version, permissions, privacy policy and Play Store listing.
- [ ] Test release build on a real device before upload.
