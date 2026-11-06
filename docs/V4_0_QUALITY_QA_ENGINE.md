# V4.0 Quality QA Engine — milestones 45–49

`scripts/quality_qa_engine.py` supplies project-scoped quality checks for Flutter
Android apps. It does not publish apps or alter release signing configuration.
All external commands are opt-in with `--execute`; the default is a read-only
dry run. Reports and full command logs are written to a new directory under the
selected app's `build/factory_quality_qa/`. Existing output paths are refused.

## Run a plan

```bash
python3 scripts/quality_qa_engine.py /path/to/flutter-app --check all
```

Select one capability with `--check tests|device|accessibility|performance|dependencies`.
Run checks that invoke Flutter, Android tooling, or a scanner explicitly:

```bash
python3 scripts/quality_qa_engine.py /path/to/flutter-app --check tests --execute
python3 scripts/quality_qa_engine.py /path/to/flutter-app --check device --execute
python3 scripts/quality_qa_engine.py /path/to/flutter-app --check performance --execute --max-apk-bytes 80000000
python3 scripts/quality_qa_engine.py /path/to/flutter-app --check performance --execute --startup-smoke --device emulator-5554
python3 scripts/quality_qa_engine.py /path/to/flutter-app --check dependencies --execute
```

The test engine discovers `test/**/*_test.dart` and
`integration_test/**/*_test.dart`. It groups unit, widget, API, offline and
regression tests using filename/directory conventions; integration tests
require an Android device serial and remain `NOT RUN` otherwise. Missing test
categories are never marked passed. Full stdout/stderr logs and failure
summaries are retained in the run directory with environment secrets redacted.

## Device and installation safety

The device check reads numeric `minSdk`/`targetSdk` values where possible,
discovers Android SDK platforms and Flutter devices, and lists compact phone,
typical phone and tablet/density profiles. A discovered device does not imply
that a screen profile was exercised; each untested profile remains `NOT RUN`.
`--smoke` additionally requires `--execute`, an explicit APK, and a unique
device selection if multiple devices exist. It refuses to install if the
application ID is already present. A successfully installed app remains on the
device; the tool never uninstalls it automatically. Permission behavior needs
app-specific scenarios and remains unverified by generic smoke tests.

## Accessibility and UX limits

Source heuristics flag interactive controls without nearby labels/semantics and
gesture controls without nearby semantics. `flutter analyze` is supplementary,
not an accessibility conformance test. TalkBack/VoiceOver order, text scaling,
overflow, keyboard focus, touch targets, contrast and UX require manual review
and are always shown as `NEEDS MANUAL VERIFICATION`.

## Performance and stability limits

With `--execute`, the performance check builds a profile APK and records actual
APK bytes and SHA-256. `--startup-smoke` additionally installs the profile APK
only when its package is absent, launches it on the selected/uniquely discovered
Android device, and records Android's `am start -W` timing output. The app
remains installed. `--max-apk-bytes` or
`APP_CONFIG.json` `quality.performance.max_apk_bytes` may set a size threshold.
Frame time, memory, crashes and stability are `NOT RUN` unless a separate
instrumented device/profile workflow supplies evidence. A profile APK size is
not an installed-size measurement.

## Dependencies, vulnerabilities, licenses and SBOM

The static report inventories lockfile package names and versions. With
`--execute`, it invokes `flutter pub deps --json` for the resolved graph. The
tool creates a CycloneDX 1.5 JSON SBOM when package inventory is available and
checks cached package metadata/license files where accessible. Unknown licenses
and review status remain visible; this is not legal approval.

Known-vulnerability scanning is separate and only runs when both
`--execute --vulnerability-scan` are passed and `osv-scanner` or `trivy` is
installed. Scanner completion alone is not represented as a clean security
assessment. Gradle runtime dependency inventory is opt-in via
`--execute --gradle-inventory`; it may require a local Android SDK and package
resolution. No scanner is installed automatically.

The existing `scripts/dependency_audit.py` remains a lightweight static-risk
review and explicitly does not claim CVE coverage. Use the quality engine when
you need the richer inventory/SBOM workflow.

## Status interpretation

- `PASS`: executed check has positive evidence within its stated scope.
- `FAIL`: an executed check found a failure.
- `PARTIAL`: limited evidence exists, requirements remain, or a check was
  blocked.
- `NOT RUN`: the check was not executed or the required tests/devices were
  absent.
- `NEEDS MANUAL VERIFICATION`: human/device interaction is still required.

No aggregate report establishes release, legal, security, accessibility, or
Play Store readiness.
