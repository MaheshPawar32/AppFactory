# Visual QA manifest guide

Copy `templates/project_docs/VISUAL_QA_MANIFEST.json` into an app's project docs and tailor it.

Example:
```json
{
  "test_commands": [
    ["flutter", "test", "integration_test/smoke_test.dart"]
  ],
  "screenshots": [
    {"name": "home_empty", "description": "Home with no records"},
    {"name": "home_populated", "description": "Home with sample records"}
  ]
}
```

Important: screenshots are taken from the current device display. The runner does not automatically drive the UI to each scenario. A person or a test harness must establish each state before capturing. Use a dedicated emulator/device without personal notifications or account data.

Manifest `test_commands` are not run unless you explicitly pass
`--execute-manifest-commands`. Commands use an argument array (not a shell), but
still run with your local user permissions; review the manifest before enabling
them. The device QA orchestrator has the same explicit flag.
