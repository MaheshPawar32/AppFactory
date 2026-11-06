#!/usr/bin/env python3
"""Read-only MyAppFactory project audit. Uses only Python's standard library."""
from pathlib import Path
import json
import re
import sys
from template_sync import compare_files

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "prompts/master_app_prompt.md",
    "docs/DEFINITION_OF_DONE.md",
    "docs/ANDROID_RELEASE_CHECKLIST.md",
    "docs/QUALITY_CHECKLIST.md",
    "docs/ACCEPTANCE_TEST_WORKFLOW.md",
    "docs/SAFE_TEMPLATE_UPDATES.md",
    "docs/TROUBLESHOOTING_HANDBOOK.md",
    "scripts/create_app.py",
    "scripts/architecture_audit.py",
    "docs/V4_0_MILESTONES_36_40.md",
    "docs/V4_0_QUALITY_QA_ENGINE.md",
    "scripts/template_update_preview.py",
    "scripts/template_sync.py",
    "scripts/dependency_audit.py",
    "scripts/quality_qa_engine.py",
    "prompts/visual_app_generation_prompt.md",
    "docs/VISUAL_APP_GENERATION_WORKFLOW.md",
    "templates/project_docs/UI_REFERENCE_INDEX.md",
    "templates/project_docs/SCREEN_INVENTORY.md",
    "templates/project_docs/PROGRESS_TRACKER.csv",
    "docs/VISUAL_REGRESSION_WORKFLOW.md",
    "docs/DEVICE_AND_ACCESSIBILITY_QA.md",
    "docs/CHANGE_IMPACT_AND_ROLLBACK.md",
    "docs/SAFE_AUTOMATION_AND_RELEASE_READINESS.md",
    "docs/DEVELOPER_DASHBOARD.md",
    "docs/RECOVERY_AND_BACKUP_WORKFLOW.md",
    "docs/OFFLINE_AND_FAILURE_STATE_TESTING.md",
    "docs/REUSABLE_FEATURE_RECIPES.md",
    "docs/ASSET_LICENSE_INVENTORY.md",
    "scripts/project_dashboard.py",
    "scripts/visual_qa_report.py",
    "scripts/release_preflight.py",
    "templates/project_docs/DEVICE_TEST_MATRIX.csv",
    "templates/project_docs/APP_CONFIG.yaml",
    "templates/project_docs/APP_CONFIG.json",
    "templates/project_docs/ASSET_LICENSE_INVENTORY.csv",
    "scripts/validate_app_config.py",
    "scripts/validate_project_registry.py",
    "scripts/asset_license_report.py",
    "scripts/screenshot_compare.py",
    "tests/test_factory_tools.py",
    "docs/V2_2_UPGRADE.md",
    "scripts/validate_flutter_project.py",
    "scripts/run_factory_checks.py",
    "docs/V2_3_UPGRADE.md",
    "docs/V2_4_UPGRADE.md",
    "docs/V2_5_UPGRADE.md",
    "docs/FACTORY_UPGRADE_ROADMAP.md",
    "docs/V3_0_BUILD_ENGINE.md",
    "docs/V3_0_ROADMAP.md",
    "scripts/app_generation_controller.py",
    "templates/project_docs/APP_BRIEF.json",
    "docs/V3_0_APP_GENERATION_CONTROLLER.md",
    "docs/V3_0_MILESTONE_2_ACCEPTANCE.md",
    "scripts/visual_qa_runner.py",
    "templates/project_docs/VISUAL_QA_MANIFEST.json",
    "docs/V3_0_VISUAL_QA.md",
    "docs/V3_0_VISUAL_QA_MANIFEST_GUIDE.md",
    "scripts/flutter_build_engine.py",
    "scripts/feature_module_manager.py",
    "templates/feature_modules/catalog.json",
    "templates/project_docs/FEATURE_MODULES.json",
    "scripts/install_runtime_kit.py",
    "templates/flutter_runtime_kit/lib/app_runtime_kit.dart",
    "docs/V3_0_MILESTONE_5_RUNTIME_KIT.md",
    "scripts/dependency_compatibility_review.py",
    "scripts/change_impact_report.py",
    "scripts/release_readiness_preflight.py",
    "docs/V3_0_MILESTONE_6_QUALITY_AUTOMATION.md",
    "templates/project_docs/QUALITY_AUTOMATION_MANIFEST.json",
    "scripts/multi_app_control_center.py",
    "docs/V3_0_MILESTONE_7_MULTI_APP_CONTROL_CENTER.md",
    "apps/PROJECT_REGISTRY.csv",
    "scripts/batch_build_pipeline.py",
    "docs/V3_0_MILESTONE_8_BATCH_BUILD_PIPELINE.md",
    "scripts/release_artifact_manager.py",
    "docs/V3_0_MILESTONE_9_RELEASE_ARTIFACT_MANAGER.md",
    "scripts/release_readiness_dashboard.py",
    "docs/V3_0_MILESTONE_10_RELEASE_READINESS_DASHBOARD.md",
    "scripts/device_qa_orchestrator.py",
    "docs/V3_0_MILESTONE_11_DEVICE_QA_ORCHESTRATOR.md",
    "scripts/app_creation_wizard.py",
    "docs/V3_0_MILESTONE_12_APP_CREATION_WIZARD.md",
    "scripts/one_command_app_workflow.py",
        "scripts/ui_screen_generator.py",
        "docs/V3_0_MILESTONE_14_UI_SCREEN_GENERATOR.md",
    "docs/V3_0_MILESTONE_13_ONE_COMMAND_WORKFLOW.md",
    "docs/V3_0_MILESTONE_14_UI_SCREEN_GENERATOR.md",
    "scripts/advanced_milestone_engine.py",
    "docs/V3_5_FINAL_MILESTONES_15_35.md",
    "docs/V3_5_FINAL_VERIFICATION.md",
    "docs/V3_5_FINAL_VERIFICATION.json",
]
REQUIRED.extend(f"scripts/milestone_{milestone}.py" for milestone in range(15, 36))
CHECKS = []
def add(name, status, detail):
    CHECKS.append({"check": name, "status": status, "detail": detail})

for rel in REQUIRED:
    add(f"Required file: {rel}", "PASS" if (ROOT / rel).is_file() else "FAIL",
        "Present" if (ROOT / rel).is_file() else "Missing")

source = ROOT / "design_system/nova_ui_flutter"
template = ROOT / "templates/nova_ui_flutter_starter"

if source.is_dir() and template.is_dir():
    comparison = compare_files(source, template)
    missing = comparison["missing"]
    extra = comparison["extra"]
    changed = comparison["different"]
    ok = not (missing or extra or changed)

    details = (f"source={len(comparison['source_files'])} "
               f"template={len(comparison['target_files'])}")
    if missing:
        details += f"; missing={missing}"
    if extra:
        details += f"; extra={extra}"
    if changed:
        details += f"; different={changed}"

    add("Nova UI starter sync", "PASS" if ok else "FAIL", details)
else:
    add("Nova UI starter sync", "FAIL", "Source or template folder is missing")

env_example = ROOT / ".env.example"
if env_example.exists():
    content = env_example.read_text(encoding="utf-8", errors="replace")
    looks_real = bool(re.search(r"(sk-[A-Za-z0-9]{16,}|AIza[0-9A-Za-z_-]{20,}|-----BEGIN (RSA |EC )?PRIVATE KEY-----)", content))
    add(".env.example placeholder scan", "REVIEW" if looks_real else "PASS",
        "Potential secret pattern found; manually inspect" if looks_real else "No common secret pattern found; this is not a full secrets scan")
else:
    add(".env.example placeholder scan", "REVIEW", "No .env.example found")

# Presence-only checks; no claim of security, compilation or correctness.
for rel, label in [
    (".gitignore", "Git ignore file"),
    ("docs/SAFE_CLAUDE_WORKFLOW.md", "Safe Claude workflow guide"),
    ("docs/DEFINITION_OF_DONE.md", "Definition of Done"),
    ("docs/SECURITY_PRIVACY_AUDIT.md", "Security/privacy audit guide"),
    ("docs/PROJECT_REGISTRY.md", "Multi-app project registry guide"),
]:
    add(label, "PASS" if (ROOT / rel).is_file() else "FAIL",
        "Present" if (ROOT / rel).is_file() else "Missing")

failed = any(c["status"] == "FAIL" for c in CHECKS)
print("MyAppFactory project audit")
print("=" * 28)
for c in CHECKS:
    print(f"[{c['status']}] {c['check']}: {c['detail']}")
print()
print("Important: this is a structural/read-only audit, not a Flutter build, security certification, or Play Store compliance check.")
print("Overall:", "FAIL" if failed else "STRUCTURAL CHECKS PASSED (manual and Flutter checks still required)")
report = ROOT / "docs/last_project_audit.json"
report.write_text(json.dumps({"checks": CHECKS, "structural_failures": failed}, indent=2), encoding="utf-8")
sys.exit(1 if failed else 0)
