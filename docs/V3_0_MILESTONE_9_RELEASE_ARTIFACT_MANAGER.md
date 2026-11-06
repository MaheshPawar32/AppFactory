# MyAppFactory v3.0 — Milestone 9: Build History & Release Artifact Manager

## Purpose
Create a local, checksum-based index of APK/AAB artifacts and discover build-engine reports for one Flutter project. The manager never signs, uploads, or publishes artifacts.

## Index artifacts and reports
```bash
python3 scripts/release_artifact_manager.py /path/to/flutter_project
```
The default index is `reports/release_artifact_index.json`; the default history file is `reports/release_history.jsonl`. Both paths can be overridden. The tool scans standard Flutter output locations and factory engine report locations.

## Record history explicitly
```bash
python3 scripts/release_artifact_manager.py /path/to/flutter_project --record-history
```
History records are appended only with `--record-history`. Artifact fingerprints use SHA-256. Re-indexing the same hash does not append another history line.

## Include additional engine reports
```bash
python3 scripts/release_artifact_manager.py /path/to/flutter_project \
  --report-dir /path/to/factory_run_folder --json
```
Repeat `--report-dir` for more report folders or direct `report.json` paths.

## Notes and safety
- APK/AAB presence is detected by file path; the manager does not prove the file installs or runs.
- SHA-256 identifies file contents; it does not establish trust or authenticity.
- Signing is reported as `NOT CHECKED`; publication as `NOT PUBLISHED`.
- Build reports are discovered separately from artifacts. Reports are not falsely assigned to unrelated artifacts.
- The index is rewritten on each run; history is only appended when explicitly requested.
- No signing credentials are read or created, and nothing is uploaded or published.
