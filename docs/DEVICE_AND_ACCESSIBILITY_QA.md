# Device, Responsive and Accessibility QA

## Minimum device matrix
Use `templates/project_docs/DEVICE_TEST_MATRIX.csv` and adapt profiles to the app's target users. Record actual device/emulator details and mark unexecuted checks `NOT RUN`.

- Compact Android viewport and a typical phone viewport.
- Large phone / tablet or resizable window where supported.
- Keyboard open on forms; scroll, focus and submit behavior.
- System font/text scaling at default and enlarged settings (at least 1.3x; include 2.0x when practical).
- Light/dark themes if supported, plus system bars and cutouts.
- Offline, slow/failing network, denied permissions and empty/error states.
- Portrait/landscape only when the app claims to support both.

## Accessibility review
- All meaningful controls have useful semantic labels and roles.
- Touch targets are comfortably usable; aim for approximately 48 logical pixels for primary interactive targets.
- Focus and reading order make sense; icon-only buttons have labels.
- Text/background contrast is reviewed; do not rely on color alone.
- Enlarged text does not hide actions or make essential content unreachable.
- Motion can be reduced or is not essential to task completion.
- Form errors are announced and associated with the relevant field.

## Evidence and honest status
- `PASS` means the test was actually executed and evidence/result recorded.
- Use `FAIL`, `BLOCKED`, or `NOT RUN`; do not convert missing evidence to pass.
- Manual accessibility review is not equivalent to a formal accessibility certification.
