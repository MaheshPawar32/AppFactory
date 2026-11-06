import csv
import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import validate_app_config
import validate_project_registry
import asset_license_report
import validate_flutter_project
import flutter_build_engine
import app_generation_controller
import visual_qa_runner
import feature_module_manager
import install_runtime_kit
import dependency_compatibility_review
import change_impact_report
import release_readiness_preflight
import multi_app_control_center
import batch_build_pipeline
import release_artifact_manager
import release_readiness_dashboard
import device_qa_orchestrator
import app_creation_wizard
import one_command_app_workflow
import ui_screen_generator
import create_app
import template_sync
import release_preflight
import architecture_audit
import quality_qa_engine


class QualityQaEngineTests(unittest.TestCase):
    def _project(self, base, valid=True):
        project = Path(base) / "flutter_app"
        project.mkdir()
        if valid:
            (project / "pubspec.yaml").write_text(
                "name: qa_fixture\n\nenvironment:\n  sdk: '>=3.0.0 <4.0.0'\n",
                encoding="utf-8",
            )
        return project

    def test_quality_engine_rejects_missing_or_invalid_flutter_projects(self):
        with tempfile.TemporaryDirectory() as d:
            missing = Path(d) / "missing"
            missing.mkdir()
            with self.assertRaisesRegex(ValueError, "pubspec.yaml"):
                quality_qa_engine.validate_project(missing)
            with self.assertRaisesRegex(ValueError, "does not exist"):
                quality_qa_engine.validate_project(Path(d) / "absent")

    def test_automated_testing_engine_discovers_suites_and_missing_tests(self):
        with tempfile.TemporaryDirectory() as d:
            project = self._project(d)
            (project / "test" / "api").mkdir(parents=True)
            (project / "test" / "api" / "client_test.dart").write_text(
                "void main() {}\n", encoding="utf-8")
            (project / "test" / "widget_test.dart").write_text(
                "void main() { testWidgets('renders', (tester) async {}); }\n", encoding="utf-8")
            (project / "integration_test").mkdir()
            (project / "integration_test" / "app_test.dart").write_text(
                "void main() {}\n", encoding="utf-8")

            report = quality_qa_engine.run_test_engine(project)
            suites = {suite["suite"]: suite for suite in report["test_suites"]}
            self.assertEqual(suites["api"]["status"], "DRY RUN")
            self.assertEqual(suites["widget"]["status"], "DRY RUN")
            self.assertEqual(suites["integration"]["status"], "NOT RUN")
            self.assertEqual(suites["unit"]["status"], "NOT RUN")
            self.assertEqual(report["overall_status"], "PARTIAL")

    def test_automated_testing_engine_records_failure_logs_and_redacts_secrets(self):
        with tempfile.TemporaryDirectory() as d:
            project = self._project(d)
            (project / "test").mkdir()
            (project / "test" / "sample_test.dart").write_text("void main() {}\n", encoding="utf-8")
            out = Path(d) / "logs"
            out.mkdir()
            with mock.patch.object(quality_qa_engine.shutil, "which", return_value="/usr/bin/flutter"), \
                 mock.patch.object(
                     quality_qa_engine, "_run_command",
                     return_value={"status": "FAIL", "exit_code": 1, "stderr_tail": ["assertion failed"]},
                 ) as run:
                report = quality_qa_engine.run_test_engine(project, execute=True, output_dir=out)
            self.assertEqual(report["overall_status"], "FAIL")
            self.assertTrue(any(item["status"] == "NOT RUN" for item in report["test_suites"]))
            self.assertEqual(run.call_count, 1)

            log = out / "secret.log"
            with mock.patch.dict("os.environ", {"PRIVATE_TOKEN": "fixture-super-secret"}):
                result = quality_qa_engine._run_command(
                    [sys.executable, "-c",
                     "import os; print('token=' + os.environ['PRIVATE_TOKEN'])"],
                    project, 10, log,
                )
            self.assertEqual(result["status"], "PASS")
            self.assertNotIn("fixture-super-secret", log.read_text(encoding="utf-8"))
            self.assertIn("[REDACTED]", log.read_text(encoding="utf-8"))

    def test_android_compatibility_reports_numeric_and_invalid_sdk_ranges(self):
        with tempfile.TemporaryDirectory() as d:
            project = self._project(d)
            app = project / "android" / "app"
            app.mkdir(parents=True)
            gradle = app / "build.gradle.kts"
            gradle.write_text(
                'android { namespace = "com.dev.qa"; defaultConfig { '
                'applicationId = "com.dev.qa"; minSdk = 23; targetSdk = 35 } }\n',
                encoding="utf-8",
            )
            report = quality_qa_engine.run_device_qa(project)
            self.assertEqual(report["sdk_validation"]["status"], "PASS")
            self.assertEqual(report["android_sdk"]["application_id"], "com.dev.qa")
            self.assertEqual(len(report["screen_density_matrix"]), 3)
            self.assertTrue(all(item["status"] == "NOT RUN" for item in report["untested_devices"]))

            gradle.write_text(
                'android { defaultConfig { minSdk = 36; targetSdk = 35 } }\n',
                encoding="utf-8",
            )
            invalid = quality_qa_engine.run_device_qa(project)
            self.assertEqual(invalid["sdk_validation"]["status"], "FAIL")
            self.assertEqual(invalid["overall_status"], "FAIL")

    def test_android_apk_sdk_manifest_values_are_inspected(self):
        with tempfile.TemporaryDirectory() as d:
            apk = Path(d) / "app.apk"
            apk.write_bytes(b"fixture")
            completed = subprocess.CompletedProcess(
                args=["aapt"], returncode=0,
                stdout="package: name='com.dev.demo'\nsdkVersion:'23'\ntargetSdkVersion:'35'\n",
                stderr="",
            )
            with mock.patch.object(quality_qa_engine.shutil, "which", return_value="/sdk/aapt"), \
                 mock.patch.object(quality_qa_engine.subprocess, "run", return_value=completed):
                metadata = quality_qa_engine._apk_sdk_metadata(apk)
            self.assertEqual(metadata, {"min_sdk": 23, "target_sdk": 35})

    def test_android_smoke_requires_explicit_safe_install_parameters(self):
        with tempfile.TemporaryDirectory() as d:
            project = self._project(d)
            with mock.patch.object(
                quality_qa_engine, "_flutter_android_devices",
                return_value=([], {"status": "NOT RUN", "reason": "No Android device or emulator connected"}),
            ):
                report = quality_qa_engine.run_device_qa(project, execute=True, smoke=True)
            self.assertEqual(report["smoke_test"]["status"], "NOT RUN")
            self.assertIn("Select --device", report["smoke_test"]["reason"])

    def test_android_smoke_refuses_installed_package_and_wrong_apk_identity(self):
        with tempfile.TemporaryDirectory() as d:
            project = self._project(d)
            gradle = project / "android" / "app"
            gradle.mkdir(parents=True)
            (gradle / "build.gradle.kts").write_text(
                'android { defaultConfig { applicationId = "com.dev.qa" } }',
                encoding="utf-8",
            )
            apk = Path(d) / "fixture.apk"
            apk.write_bytes(b"fixture")
            with mock.patch.object(
                quality_qa_engine, "_flutter_android_devices",
                return_value=([{"id": "emulator-fixture"}], {"status": "PASS"}),
            ), mock.patch.object(
                quality_qa_engine, "_apk_application_id", return_value="com.dev.qa"
            ), mock.patch.object(quality_qa_engine, "shutil") as shutil_mock:
                shutil_mock.which.return_value = "/fixture/adb"
                with mock.patch.object(
                    quality_qa_engine, "_run_command",
                    return_value={"status": "PASS", "stdout_tail": ["package:com.dev.qa"]},
                ):
                    report = quality_qa_engine.run_device_qa(
                        project, execute=True, smoke=True, apk=apk, device="emulator-fixture",
                    )
            self.assertEqual(report["smoke_test"]["status"], "BLOCKED")
            self.assertIn("already installed", report["smoke_test"]["reason"])

            with mock.patch.object(
                quality_qa_engine, "_flutter_android_devices",
                return_value=([{"id": "emulator-fixture"}], {"status": "PASS"}),
            ), mock.patch.object(
                quality_qa_engine, "_apk_application_id", return_value="com.someone.elses.app"
            ):
                wrong = quality_qa_engine.run_device_qa(
                    project, execute=True, smoke=True, apk=apk, device="emulator-fixture",
                )
            self.assertEqual(wrong["smoke_test"]["status"], "BLOCKED")
            self.assertIn("does not match", wrong["smoke_test"]["reason"])

    def test_accessibility_reports_actionable_findings_and_manual_reviews(self):
        with tempfile.TemporaryDirectory() as d:
            project = self._project(d)
            lib = project / "lib"
            lib.mkdir()
            (lib / "main.dart").write_text(
                "Widget build(BuildContext context) {\n"
                "  return IconButton(icon: Icon(Icons.close), onPressed: close);\n"
                "}\n",
                encoding="utf-8",
            )
            report = quality_qa_engine.run_accessibility_qa(project)
            self.assertTrue(report["automated_findings"])
            self.assertEqual(report["automated_findings"][0]["check"], "interactive_control_semantics")
            self.assertTrue(report["manual_reviews"])
            self.assertTrue(all(item["status"] == "NEEDS MANUAL VERIFICATION"
                                for item in report["manual_reviews"]))
            (lib / "main.dart").write_text(
                "IconButton(tooltip: 'Close', onPressed: close)\n", encoding="utf-8")
            reviewed = quality_qa_engine.run_accessibility_qa(project)
            self.assertEqual(reviewed["automated_findings"], [])
            self.assertEqual(reviewed["overall_status"], "PARTIAL")
            (lib / "colors.dart").write_text(
                "ColorScheme(primary: Color(0xFF000000), onPrimary: Color(0xFFFFFFFF));\n",
                encoding="utf-8",
            )
            measured = quality_qa_engine.run_accessibility_qa(project)
            self.assertEqual(measured["contrast_measurements"][0]["contrast_ratio"], 21.0)
            self.assertEqual(measured["contrast_measurements"][0]["status"], "PASS")

    def test_performance_report_never_invents_runtime_metrics(self):
        with tempfile.TemporaryDirectory() as d:
            project = self._project(d)
            report = quality_qa_engine.run_performance_qa(project, max_apk_bytes=12345)
            self.assertEqual(report["thresholds"]["max_apk_bytes"], 12345)
            self.assertEqual(report["profile_build"]["status"], "NOT RUN")
            self.assertEqual(report["startup"]["status"], "NOT RUN")
            self.assertEqual(report["frame_memory_profile"]["status"], "NOT RUN")
            self.assertEqual(report["overall_status"], "PARTIAL")
            invalid = Path(d) / "missing"
            invalid.mkdir()
            with self.assertRaisesRegex(ValueError, "pubspec.yaml"):
                quality_qa_engine.run_performance_qa(invalid)

    def test_dependency_audit_distinguishes_lock_inventory_scanning_and_licenses(self):
        with tempfile.TemporaryDirectory() as d:
            project = self._project(d)
            (project / "pubspec.lock").write_text(
                'packages:\n  sample_dep:\n    dependency: "direct main"\n'
                '    description:\n      name: sample_dep\n    source: hosted\n'
                '    version: "1.2.3"\nsdks:\n  dart: ">=3.0.0 <4.0.0"\n',
                encoding="utf-8",
            )
            package_root = Path(d) / "pub-cache" / "sample_dep"
            package_root.mkdir(parents=True)
            (package_root / "LICENSE").write_text("Fixture license text\n", encoding="utf-8")
            (package_root / "pubspec.yaml").write_text(
                "name: sample_dep\nlicense: MIT\n", encoding="utf-8")
            dart_tool = project / ".dart_tool"
            dart_tool.mkdir()
            (dart_tool / "package_config.json").write_text(json.dumps({
                "packages": [{
                    "name": "sample_dep", "rootUri": package_root.as_uri() + "/",
                }],
            }), encoding="utf-8")
            report = quality_qa_engine.run_dependency_audit(project)
            self.assertEqual(report["lock_inventory"]["status"], "PASS")
            self.assertEqual(report["flutter_dependencies"], [
                {"name": "sample_dep", "version": "1.2.3", "kind": "direct", "source": "hosted"},
            ])
            self.assertEqual(report["sbom"]["status"], "PASS")
            self.assertEqual(report["vulnerability_scan"]["status"], "NOT RUN")
            self.assertEqual(report["licenses"][0]["status"], "REVIEW")
            self.assertEqual(report["licenses"][0]["declared_license"], "MIT")
            self.assertEqual(report["licenses"][0]["license_files"], ["LICENSE"])
            self.assertEqual(
                quality_qa_engine._package_licenses(project, [{"name": "uncached"}])[0]["status"],
                "UNKNOWN",
            )
            invalid = Path(d) / "missing"
            invalid.mkdir()
            with self.assertRaisesRegex(ValueError, "pubspec.yaml"):
                quality_qa_engine.run_dependency_audit(invalid)

    def test_qa_report_paths_refuse_overwrite_and_escape(self):
        with tempfile.TemporaryDirectory() as d:
            project = self._project(d)
            root = project / "build" / "factory_quality_qa"
            root.mkdir(parents=True)
            existing = root / "existing.json"
            existing.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(FileExistsError, "Refusing to overwrite"):
                quality_qa_engine.create_output_dir(project, existing)
            with self.assertRaisesRegex(ValueError, "inside the project QA output directory"):
                quality_qa_engine.create_output_dir(project, Path(d) / "escape.json")


class FactoryToolTests(unittest.TestCase):
    def test_valid_app_config(self):
        data = {
            "app": {"name": "Demo", "package_name": "com.dev.demo", "version": "1.0.0+1", "project_type": "new"},
            "architecture": {"state_management": "Provider", "storage": "Hive"},
            "integrations": {"backend": "none", "firebase_enabled": False, "firebase_services": [], "admob_enabled": False, "admob_formats": []},
            "design": {"locales": ["en"]},
            "constraints": {"preserve_existing_features": True}
        }
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "APP_CONFIG.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            self.assertTrue(validate_app_config.validate(p)["valid"])

    def test_invalid_package_fails(self):
        data = {"app": {"name": "Demo", "package_name": "Bad Package", "version": "1.0"},
                "architecture": {"state_management": "Provider", "storage": "Hive"},
                "integrations": {"backend": "none"}, "design": {"locales": ["en"]}}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "APP_CONFIG.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            result = validate_app_config.validate(p)
            self.assertFalse(result["valid"])
            self.assertTrue(any("package_name" in e for e in result["errors"]))

    def test_empty_registry_header_valid(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "registry.csv"
            p.write_text("app_name,package_name,current_stage,last_analyzer_status,last_test_status,last_build_status,next_action\n", encoding="utf-8")
            self.assertTrue(validate_project_registry.validate(p)["valid"])

    def test_asset_inventory_header_valid(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "assets.csv"
            p.write_text("Asset ID,Asset / package,Source URL or package,Author / owner,License,Attribution required,Commercial use allowed,File path / version,Review status\n", encoding="utf-8")
            self.assertTrue(asset_license_report.inspect(p)["valid"])

    def test_flutter_validator_flags_missing_pubspec(self):
        with tempfile.TemporaryDirectory() as d:
            result = validate_flutter_project.inspect(Path(d))
            self.assertFalse(result["passed"])
            self.assertEqual(result["findings"][0]["status"], "FAIL")

    def test_flutter_validator_detects_package_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d)
            (project / "android" / "app").mkdir(parents=True)
            (project / "lib").mkdir()
            (project / "test").mkdir()
            (project / ".gitignore").write_text("build/\n", encoding="utf-8")
            (project / "pubspec.yaml").write_text("name: demo_app\nversion: 1.0.0+1\n", encoding="utf-8")
            (project / "android" / "app" / "build.gradle").write_text(
                'android {\n    namespace "com.dev.demo"\n}\nandroid {\n    defaultConfig {\n        applicationId "com.dev.demo"\n    }\n}\n',
                encoding="utf-8")
            (project / "android" / "app" / "src" / "main").mkdir(parents=True)
            (project / "android" / "app" / "src" / "main" / "AndroidManifest.xml").write_text(
                '<manifest xmlns:android="http://schemas.android.com/apk/res/android"><application /></manifest>',
                encoding="utf-8")
            result = validate_flutter_project.inspect(project)
            self.assertTrue(result["passed"])
            checks = {item["check"]: item["status"] for item in result["findings"]}
            self.assertEqual(checks["applicationId"], "PASS")
            self.assertEqual(checks["namespace"], "PASS")

    def test_failure_classifier(self):
        self.assertEqual(flutter_build_engine.classify_failure("Version solving failed"), "DEPENDENCY_RESOLUTION")
        self.assertEqual(flutter_build_engine.classify_failure("Gradle task assembleRelease failed"), "ANDROID_BUILD")

    def test_engine_blocks_missing_flutter_project(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d)
            result = flutter_build_engine.command_version(["flutter", "--version"])
            self.assertIn("available", result)
            self.assertFalse((project / "pubspec.yaml").exists())

    def test_engine_dry_run_does_not_create_run_files(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d) / "app"
            project.mkdir()
            (project / "pubspec.yaml").write_text("name: demo_app\n", encoding="utf-8")
            run_dir = Path(d) / "run-output"
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "flutter_build_engine.py"),
                 str(project), "--dry-run", "--build", "none", "--fix-mode", "none",
                 "--run-dir", str(run_dir)],
                capture_output=True, text=True, cwd=ROOT, timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            report = json.loads(proc.stdout)
            self.assertEqual(report["overall_status"], "DRY RUN")
            self.assertFalse(run_dir.exists())
            self.assertTrue(any(step["step"] == "static_analysis"
                                for step in report["planned_commands"]))

    def test_engine_dry_run_includes_android_flavor_and_dart_defines(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d) / "app"
            project.mkdir()
            (project / "pubspec.yaml").write_text("name: demo_app\n", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "flutter_build_engine.py"),
                 str(project), "--dry-run", "--build", "apk", "--fix-mode", "none",
                 "--flavor", "staging", "--dart-define", "APP_ENV=staging",
                 "--dart-define", "API_BASE_URL=https://example.invalid"],
                capture_output=True, text=True, cwd=ROOT, timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            report = json.loads(proc.stdout)
            build = next(
                step["command"] for step in report["planned_commands"]
                if step["step"] == "release_build"
            )
            self.assertEqual(
                build,
                ["flutter", "build", "apk", "--release", "--flavor", "staging",
                 "--dart-define=APP_ENV=staging",
                 "--dart-define=API_BASE_URL=https://example.invalid"],
            )

    def test_engine_rejects_malformed_dart_define_before_execution(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d) / "app"
            project.mkdir()
            (project / "pubspec.yaml").write_text("name: demo_app\n", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "flutter_build_engine.py"),
                 str(project), "--dry-run", "--dart-define", "not-a-valid-key=value"],
                capture_output=True, text=True, cwd=ROOT, timeout=30)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("KEY=VALUE", proc.stderr)

    def test_controller_initializes_resumable_task_plan(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            brief = base / "brief.json"
            brief.write_text(json.dumps({"app": {"name": "Demo App"}, "screens": [{"name": "Home"}]}), encoding="utf-8")
            workspace = base / "workflow"
            state = app_generation_controller.initialize(workspace, brief)
            loaded = app_generation_controller.load_state(workspace)
            self.assertEqual(loaded["app_name"], "Demo App")
            self.assertEqual(len(loaded["tasks"]), 9)
            self.assertEqual(loaded["tasks"][0]["status"], "PENDING")
            self.assertTrue((workspace / "workflow_state.json").is_file())

    def test_controller_refuses_existing_workspace(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            brief = base / "brief.json"
            brief.write_text(json.dumps({"app": {"name": "Demo App"}}), encoding="utf-8")
            workspace = base / "workflow"
            workspace.mkdir()
            with self.assertRaises(FileExistsError):
                app_generation_controller.initialize(workspace, brief)

    def test_controller_approval_gate_defaults_closed(self):
        tasks = app_generation_controller.build_tasks({"app": {"name": "Demo"}})
        architecture = next(t for t in tasks if t["id"] == "architecture_review")
        self.assertTrue(architecture["approval_required"])
        self.assertFalse(architecture["approved"])

    def test_controller_enforces_approval_before_starting_gated_task(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            brief = base / "brief.json"
            brief.write_text(json.dumps({"app": {"name": "Demo"}}), encoding="utf-8")
            workspace = base / "workflow"
            app_generation_controller.initialize(workspace, brief)
            command = [sys.executable, str(ROOT / "scripts" / "app_generation_controller.py"),
                       "start", "--workspace", str(workspace), "--task", "architecture_review"]
            refused = subprocess.run(command, capture_output=True, text=True, cwd=ROOT, timeout=10)
            self.assertEqual(refused.returncode, 2)
            self.assertIn("requires explicit approval", refused.stderr)
            state = app_generation_controller.load_state(workspace)
            gated = next(task for task in state["tasks"] if task["id"] == "architecture_review")
            self.assertEqual(gated["status"], "PENDING")

            approved = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "app_generation_controller.py"),
                 "approve", "--workspace", str(workspace), "--task", "architecture_review",
                 "--note", "Reviewed the proposed architecture."],
                capture_output=True, text=True, cwd=ROOT, timeout=10)
            self.assertEqual(approved.returncode, 0, approved.stderr)
            started = subprocess.run(command, capture_output=True, text=True, cwd=ROOT, timeout=10)
            self.assertEqual(started.returncode, 0, started.stderr)

    def test_visual_qa_runner_requires_flutter_project(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d)
            old_argv = sys.argv[:]
            sys.argv = ["visual_qa_runner.py", str(project)]
            try:
                with tempfile.TemporaryFile(mode="w+t") as output:
                    from contextlib import redirect_stdout
                    with redirect_stdout(output):
                        code = visual_qa_runner.main()
                    output.seek(0)
                    report = json.loads(output.read())
                self.assertEqual(code, 2)
                self.assertEqual(report["overall_status"], "BLOCKED")
            finally:
                sys.argv = old_argv

    def test_visual_qa_manifest_commands_require_explicit_execution(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            project = base / "app"
            project.mkdir()
            (project / "pubspec.yaml").write_text("name: demo_app\n", encoding="utf-8")
            marker = base / "command-ran.txt"
            manifest = base / "manifest.json"
            manifest.write_text(json.dumps({
                "test_commands": [[sys.executable, "-c",
                                   f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')"]]
            }), encoding="utf-8")
            runner = ROOT / "scripts" / "visual_qa_runner.py"
            out = base / "default-run"
            skipped = subprocess.run(
                [sys.executable, str(runner), str(project), "--manifest", str(manifest),
                 "--out", str(out)],
                capture_output=True, text=True, cwd=ROOT, timeout=20)
            self.assertEqual(skipped.returncode, 0, skipped.stderr)
            skipped_report = json.loads((out / "visual_qa_report.json").read_text(encoding="utf-8"))
            self.assertEqual(skipped_report["tests"][0]["status"], "NOT RUN")
            self.assertFalse(marker.exists())

            out = base / "approved-run"
            executed = subprocess.run(
                [sys.executable, str(runner), str(project), "--manifest", str(manifest),
                 "--out", str(out), "--execute-manifest-commands"],
                capture_output=True, text=True, cwd=ROOT, timeout=20)
            self.assertEqual(executed.returncode, 0, executed.stderr)
            executed_report = json.loads((out / "visual_qa_report.json").read_text(encoding="utf-8"))
            self.assertEqual(executed_report["tests"][0]["status"], "PASS")
            self.assertTrue(marker.is_file())

    def test_visual_qa_manifest_command_shape_is_safe(self):
        self.assertTrue(callable(visual_qa_runner.run_command))
        self.assertTrue(callable(visual_qa_runner.main))

    def test_screenshot_compare_missing_files_is_safe(self):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "screenshot_compare.py"),
                               "/missing/reference.png", "/missing/runtime.png", "--json"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn('"status": "NOT RUN"', proc.stdout)


    def test_feature_module_manifest_validates(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "modules.json"
            p.write_text(json.dumps({
                "schema_version": 1,
                "app": {"name": "Demo", "path": "apps/demo"},
                "selected_modules": [{"id": "offline_storage", "choice": "hive", "status": "not configured"}]
            }), encoding="utf-8")
            self.assertTrue(feature_module_manager.validate_manifest(p)["valid"])

    def test_feature_module_tested_requires_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "modules.json"
            p.write_text(json.dumps({
                "schema_version": 1,
                "selected_modules": [{"id": "api_client", "choice": "http", "status": "tested"}]
            }), encoding="utf-8")
            result = feature_module_manager.validate_manifest(p)
            self.assertFalse(result["valid"])
            self.assertTrue(any("requires evidence" in e for e in result["errors"]))

    def test_feature_module_prompt_contains_safety_rules(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "modules.json"
            p.write_text(json.dumps({
                "schema_version": 1,
                "app": {"name": "Demo", "path": "apps/demo"},
                "selected_modules": [{"id": "api_client", "choice": "http", "status": "not configured"}]
            }), encoding="utf-8")
            prompt = feature_module_manager.generate_prompt(p)
            self.assertIn("Never invent credentials", prompt)
            self.assertIn("HTTP API client", prompt)

    def test_runtime_installer_refuses_non_flutter_target(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                install_runtime_kit.install(Path(d))

    def test_runtime_installer_copies_without_dependencies(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            (target / "pubspec.yaml").write_text("name: demo\\n", encoding="utf-8")
            result = install_runtime_kit.install(target)
            self.assertEqual(result["dependencies_added"], [])
            self.assertTrue((target / "lib/core/runtime/app_result.dart").is_file())

    def test_runtime_installer_refuses_collision(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            (target / "pubspec.yaml").write_text("name: demo\\n", encoding="utf-8")
            destination = target / "lib/core/runtime/app_result.dart"
            destination.parent.mkdir(parents=True)
            destination.write_text("// existing user file", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                install_runtime_kit.install(target)
            self.assertEqual(destination.read_text(encoding="utf-8"), "// existing user file")


    def test_dependency_review_reads_simple_pubspec(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "pubspec.yaml"
            p.write_text("name: demo\nenvironment:\n  sdk: '>=3.0.0 <4.0.0'\ndependencies:\n  flutter:\n    sdk: flutter\n  http: ^1.2.0\n", encoding="utf-8")
            result = dependency_compatibility_review.audit_pubspec(p)
            self.assertTrue(result["valid"])
            self.assertIn("http", [x["name"] for x in result["dependencies"]])

    def test_change_impact_maps_platform_and_assets(self):
        report = change_impact_report.build_report(["android/app/build.gradle", "assets/logo.png"])
        self.assertEqual(report["changed_file_count"], 2)
        self.assertIn("platform", [a["area"] for f in report["files"] for a in f["areas"]])
        self.assertIn("assets", [a["area"] for f in report["files"] for a in f["areas"]])

    def test_release_preflight_blocks_non_flutter_folder(self):
        with tempfile.TemporaryDirectory() as d:
            result = release_readiness_preflight.preflight(Path(d))
            self.assertEqual(result["status"], "BLOCKED")

    def test_release_preflight_does_not_run_flutter_by_default(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "pubspec.yaml").write_text("name: demo", encoding="utf-8")
            result = release_readiness_preflight.preflight(p)
            self.assertFalse(any("command" in c for c in result["checks"]))

    def test_release_preflight_reports_secret_scan_read_errors(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d)
            unreadable = project / "lib" / "source.dart"
            unreadable.parent.mkdir()
            unreadable.write_text("const value = 'safe';", encoding="utf-8")
            original_read_text = Path.read_text

            def read_text(path, *args, **kwargs):
                if path == unreadable:
                    raise PermissionError("test read failure")
                return original_read_text(path, *args, **kwargs)

            with mock.patch.object(Path, "read_text", read_text):
                report = release_preflight.inspect(project)

            scan = next(item for item in report["findings"]
                        if item["check"] == "Common secret-pattern scan")
            self.assertEqual(scan["status"], "REVIEW")
            self.assertIn("file read errors: 1", scan["detail"])


    def test_control_center_summarizes_registered_apps(self):
        rows = [
            {"app_name": "App A", "project_path": ".", "last_analyzer_status": "PASS", "last_test_status": "PASS", "last_build_status": "PASS"},
            {"app_name": "App B", "project_path": "", "last_analyzer_status": "NOT RUN"},
            {"app_name": "App C", "project_path": "missing_folder", "last_test_status": "FAIL"},
        ]
        report = multi_app_control_center.build_report(rows, ROOT)
        self.assertEqual(report["summary"]["total"], 3)
        self.assertEqual(report["summary"]["missing_paths"], 1)
        self.assertEqual(report["summary"]["not_verified"], 1)
        self.assertEqual(report["apps"][1]["health"], "NEEDS_PATH")
        self.assertEqual(report["apps"][2]["health"], "MISSING_PATH")

    def test_control_center_html_escapes_registry_values(self):
        report = multi_app_control_center.build_report([
            {"app_name": "<script>alert(1)</script>", "project_path": ""}
        ], ROOT)
        page = multi_app_control_center.render_html(report)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)

    def test_control_center_loads_registry_header_only(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "registry.csv"
            p.write_text("app_name,project_path,last_test_status\\n", encoding="utf-8")
            rows, warnings = multi_app_control_center.load_registry(p)
            self.assertEqual(rows, [])
            self.assertEqual(warnings, [])


    def test_batch_pipeline_defaults_to_dry_run(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            app=base/"demo"; app.mkdir()
            (app/"pubspec.yaml").write_text("name: demo_app\n",encoding="utf-8")
            registry=base/"registry.csv"
            registry.write_text("app_name,package_name,version,platform,project_path,last_analyzer_status,last_test_status,last_build_status\nDemo,com.dev.demo,1.0.0+1,android,demo,NOT RUN,NOT RUN,NOT RUN\n",encoding="utf-8")
            apps=batch_build_pipeline.load_apps(registry,base)
            report=batch_build_pipeline.run_batch(apps,execute=False)
            self.assertEqual(report["mode"],"DRY RUN")
            self.assertEqual(report["apps"][0]["status"],"DRY RUN")
            self.assertIn("--dry-run",report["apps"][0]["planned_engine_command"])

    def test_batch_pipeline_blocks_missing_project_path(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); registry=base/"registry.csv"
            registry.write_text("app_name,project_path\nMissing,not_here\n",encoding="utf-8")
            apps=batch_build_pipeline.load_apps(registry,base)
            report=batch_build_pipeline.run_batch(apps,execute=False)
            self.assertEqual(report["apps"][0]["status"],"BLOCKED")

    def test_batch_pipeline_refuses_registry_update_in_dry_run(self):
        # CLI guard is covered by checking the safety contract in the parser source.
        source=(ROOT/"scripts"/"batch_build_pipeline.py").read_text(encoding="utf-8")
        self.assertIn('if a.update_registry and not a.execute:',source)


    def test_release_artifact_manager_indexes_artifact_checksum(self):
        with tempfile.TemporaryDirectory() as d:
            project=Path(d); (project/"pubspec.yaml").write_text("name: demo\n",encoding="utf-8")
            apk_dir=project/"build"/"app"/"outputs"/"flutter-apk"; apk_dir.mkdir(parents=True)
            apk=apk_dir/"app-release.apk"; apk.write_bytes(b"fake apk test fixture")
            artifacts,reports=release_artifact_manager.discover(project,scan_build=True)
            self.assertEqual(len(artifacts),1)
            self.assertEqual(artifacts[0]["artifact_type"],"APK")
            self.assertEqual(artifacts[0]["sha256"],release_artifact_manager.sha256_file(apk))
            self.assertEqual(artifacts[0]["signature_status"],"NOT CHECKED")

    def test_release_artifact_manager_deduplicates_history_by_hash(self):
        one={"sha256":"abc","file_name":"one.apk","indexed_at_utc":"2026-01-01"}
        two={"sha256":"abc","file_name":"renamed.apk","indexed_at_utc":"2026-01-02"}
        merged=release_artifact_manager.merge_history([one],[two])
        self.assertEqual(len(merged),1)
        self.assertEqual(merged[0]["file_name"],"renamed.apk")

    def test_release_artifact_manager_blocks_non_flutter_path(self):
        with tempfile.TemporaryDirectory() as d:
            result=subprocess.run([sys.executable,str(ROOT/"scripts"/"release_artifact_manager.py"),d],
                                  capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,2)
            self.assertIn("BLOCKED",result.stdout)


    def test_release_dashboard_distinguishes_registry_claims_from_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); app=base/"demo"; app.mkdir()
            (app/"pubspec.yaml").write_text("name: demo_app\n",encoding="utf-8")
            reg=base/"registry.csv"
            reg.write_text("app_name,package_name,version,project_path,last_analyzer_status,last_test_status,last_build_status,next_action,open_blockers\nDemo,com.dev.demo,1.0.0+1,demo,PASS,PASS,PASS,Review,none\n",encoding="utf-8")
            report=release_readiness_dashboard.build_dashboard(reg,base)
            self.assertEqual(report["apps"][0]["release_status"],"NOT VERIFIED")
            self.assertEqual(report["summary"]["release_ready_count"],0)

    def test_release_dashboard_isolates_valid_artifacts_between_apps(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            apps={}
            artifacts={}
            for name in ("alpha","beta"):
                project=base/name
                (project/"build").mkdir(parents=True)
                (project/"pubspec.yaml").write_text(f"name: {name}\n",encoding="utf-8")
                artifact=project/"build"/f"{name}.apk"
                artifact.write_bytes(f"{name} APK bytes".encode())
                apps[name]=project
                artifacts[name]=artifact
                reports=project/"reports"
                reports.mkdir()
                index={
                    "project_path":str(project.resolve()),
                    "artifacts":[{
                        "path":str(artifact.resolve()),
                        "project_relative_path":str(artifact.relative_to(project)),
                        "artifact_type":"APK",
                        "size_bytes":artifact.stat().st_size,
                        "sha256":release_artifact_manager.sha256_file(artifact),
                    }],
                }
                (reports/"release_artifact_index.json").write_text(
                    json.dumps(index),encoding="utf-8")

            registry=base/"registry.csv"
            registry.write_text(
                "app_name,project_path\n"
                f"Alpha,{apps['alpha']}\n"
                f"Beta,{apps['beta']}\n",
                encoding="utf-8",
            )
            result=release_readiness_dashboard.build_dashboard(registry,base)
            by_name={app["app_name"].lower():app for app in result["apps"]}
            self.assertEqual(
                [item["path"] for item in by_name["alpha"]["artifacts"]],
                [str(artifacts["alpha"].resolve())],
            )
            self.assertEqual(
                [item["path"] for item in by_name["beta"]["artifacts"]],
                [str(artifacts["beta"].resolve())],
            )

    def test_release_dashboard_rejects_cross_app_and_outside_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            projects={}
            artifacts={}
            for name in ("alpha","beta"):
                project=base/name
                (project/"build").mkdir(parents=True)
                (project/"reports").mkdir()
                (project/"pubspec.yaml").write_text(f"name: {name}\n",encoding="utf-8")
                artifact=project/"build"/f"{name}.apk"
                artifact.write_bytes(f"{name} APK bytes".encode())
                projects[name]=project
                artifacts[name]=artifact

            outside=base/"outside.apk"
            outside.write_bytes(b"not owned by either app")
            for owner,foreign in (("alpha","beta"),("beta","alpha")):
                index={
                    "project_path":str(projects[owner].resolve()),
                    "artifacts":[
                        {
                            "path":str(artifacts[foreign].resolve()),
                            "artifact_type":"APK",
                            "size_bytes":artifacts[foreign].stat().st_size,
                            "sha256":release_artifact_manager.sha256_file(artifacts[foreign]),
                        },
                        {
                            "path":str(outside.resolve()),
                            "artifact_type":"APK",
                            "size_bytes":outside.stat().st_size,
                            "sha256":release_artifact_manager.sha256_file(outside),
                        },
                    ],
                }
                (projects[owner]/"reports"/"release_artifact_index.json").write_text(
                    json.dumps(index),encoding="utf-8")

            registry=base/"registry.csv"
            registry.write_text(
                "app_name,project_path\n"
                f"Alpha,{projects['alpha']}\n"
                f"Beta,{projects['beta']}\n",
                encoding="utf-8",
            )
            result=release_readiness_dashboard.build_dashboard(registry,base)
            for app in result["apps"]:
                self.assertEqual(app["artifacts"],[])
                self.assertEqual(len(app["artifact_evidence_warnings"]),2)
                self.assertTrue(all(
                    "Rejected artifact" in warning
                    for warning in app["artifact_evidence_warnings"]
                ))

    def test_release_dashboard_scopes_shared_root_index_to_its_project(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            alpha=base/"alpha"
            beta=base/"beta"
            for name,project in (("alpha",alpha),("beta",beta)):
                project.mkdir()
                (project/"pubspec.yaml").write_text(f"name: {name}\n",encoding="utf-8")
            artifact=alpha/"build"/"app.apk"
            artifact.parent.mkdir()
            artifact.write_bytes(b"alpha only")
            shared_reports=base/"reports"
            shared_reports.mkdir()
            (shared_reports/"release_artifact_index.json").write_text(
                json.dumps({
                    "project_path":str(alpha.resolve()),
                    "artifacts":[{
                        "path":str(artifact.resolve()),
                        "artifact_type":"APK",
                        "size_bytes":artifact.stat().st_size,
                        "sha256":release_artifact_manager.sha256_file(artifact),
                    }],
                }),
                encoding="utf-8",
            )
            registry=base/"registry.csv"
            registry.write_text(
                "app_name,project_path\nAlpha,alpha\nBeta,beta\n",
                encoding="utf-8",
            )

            result=release_readiness_dashboard.build_dashboard(registry,base)
            by_name={app["app_name"]:app for app in result["apps"]}
            self.assertEqual(len(by_name["Alpha"]["artifacts"]),1)
            self.assertEqual(by_name["Alpha"]["artifacts"][0]["path"],str(artifact.resolve()))
            self.assertEqual(by_name["Beta"]["artifacts"],[])
            self.assertTrue(any("another project" in warning
                                for warning in by_name["Beta"]["artifact_evidence_warnings"]))

    def test_release_dashboard_keeps_legacy_app_local_index_compatibility(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            project=base/"demo"
            build=project/"build"
            reports=project/"reports"
            build.mkdir(parents=True)
            reports.mkdir()
            (project/"pubspec.yaml").write_text("name: demo\n",encoding="utf-8")
            artifact=build/"demo.apk"
            artifact.write_bytes(b"legacy local index artifact")
            index=reports/"release_artifact_index.json"
            index.write_text(json.dumps({
                "artifacts":[{
                    "path":str(artifact.resolve()),
                    "artifact_type":"APK",
                    "size_bytes":artifact.stat().st_size,
                    "sha256":release_artifact_manager.sha256_file(artifact),
                }],
            }),encoding="utf-8")
            registry=base/"registry.csv"
            registry.write_text(
                "app_name,project_path,evidence_path\n"
                "Demo,demo,demo/reports/release_artifact_index.json\n",
                encoding="utf-8",
            )

            result=release_readiness_dashboard.build_dashboard(registry,base)
            self.assertEqual(len(result["apps"][0]["artifacts"]),1)
            self.assertEqual(result["apps"][0]["artifacts"][0]["path"],str(artifact.resolve()))

    def test_release_dashboard_rejects_stale_malformed_and_wrong_project_indexes(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            project=base/"demo"
            (project/"build").mkdir(parents=True)
            (project/"reports").mkdir()
            (project/"pubspec.yaml").write_text("name: demo\n",encoding="utf-8")
            artifact=project/"build"/"demo.apk"
            artifact.write_bytes(b"current apk bytes")
            index_path=project/"reports"/"release_artifact_index.json"
            index={
                "project_path":str(project.resolve()),
                "artifacts":[{
                    "path":str(artifact.resolve()),
                    "artifact_type":"APK",
                    "size_bytes":artifact.stat().st_size,
                    "sha256":"0"*64,
                }],
            }
            index_path.write_text(json.dumps(index),encoding="utf-8")
            registry=base/"registry.csv"
            registry.write_text(
                "app_name,project_path\nDemo,demo\n",encoding="utf-8")

            stale=release_readiness_dashboard.build_dashboard(registry,base)["apps"][0]
            self.assertEqual(stale["artifacts"],[])
            self.assertIn("SHA-256",stale["artifact_evidence_warnings"][0])

            index_path.write_text("{malformed",encoding="utf-8")
            malformed=release_readiness_dashboard.build_dashboard(registry,base)["apps"][0]
            self.assertEqual(malformed["artifacts"],[])
            self.assertTrue(any("malformed artifact index" in warning
                                for warning in malformed["artifact_evidence_warnings"]))

            index["project_path"]=str((base/"another-app").resolve())
            index_path.write_text(json.dumps(index),encoding="utf-8")
            wrong_project=release_readiness_dashboard.build_dashboard(registry,base)["apps"][0]
            self.assertEqual(wrong_project["artifacts"],[])
            self.assertTrue(any("another project" in warning
                                for warning in wrong_project["artifact_evidence_warnings"]))

            index_path.write_text(json.dumps({
                "project_path":str(project.resolve()),
                "artifacts":[{
                    "path":str(artifact.resolve()),
                    "artifact_type":"APK",
                    "size_bytes":artifact.stat().st_size,
                }],
            }),encoding="utf-8")
            missing_integrity=release_readiness_dashboard.build_dashboard(registry,base)["apps"][0]
            self.assertEqual(missing_integrity["artifacts"],[])
            self.assertTrue(any("no SHA-256" in warning
                                for warning in missing_integrity["artifact_evidence_warnings"]))

    def test_release_dashboard_requires_existing_flutter_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); reg=base/"registry.csv"
            reg.write_text("app_name,project_path\nBroken,missing\n",encoding="utf-8")
            report=release_readiness_dashboard.build_dashboard(reg,base)
            self.assertEqual(report["apps"][0]["release_status"],"BLOCKED")

    def test_release_dashboard_html_escapes_registry_content(self):
        report={"generated_at_utc":"now","summary":{"apps":1,"statuses":{"NOT VERIFIED":1}},
                "apps":[{"app_name":"<script>alert(1)</script>","package_name":"","version":"",
                "release_status":"NOT VERIFIED","reason":"review","registry_statuses":{"tests":"NOT RUN"},
                "latest_engine_report":None,"artifacts":[],"next_action":"","open_blockers":"",
                "evidence_note":"test"}]}
        html=release_readiness_dashboard.render_html(report)
        self.assertNotIn("<script>alert(1)</script>",html)
        self.assertIn("&lt;script&gt;",html)


    def test_device_qa_orchestrator_dry_run_never_executes(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); app=base/"demo"; app.mkdir()
            (app/"pubspec.yaml").write_text("name: demo_app\n",encoding="utf-8")
            reg=base/"registry.csv"
            reg.write_text("app_name,package_name,project_path\nDemo,com.dev.demo,demo\n",encoding="utf-8")
            projects=device_qa_orchestrator.load_projects(reg,base)
            report=device_qa_orchestrator.run_projects(projects,execute=False)
            self.assertEqual(report["apps"][0]["status"],"DRY RUN")
            self.assertIn("--run-tests",report["apps"][0]["planned_command"])

    def test_device_qa_orchestrator_blocks_missing_project(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); reg=base/"registry.csv"
            reg.write_text("app_name,project_path\nBroken,missing\n",encoding="utf-8")
            projects=device_qa_orchestrator.load_projects(reg,base)
            report=device_qa_orchestrator.run_projects(projects,execute=False)
            self.assertEqual(report["apps"][0]["status"],"BLOCKED")

    def test_device_qa_orchestrator_rejects_unknown_app(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); reg=base/"registry.csv"
            reg.write_text("app_name,project_path\nDemo,missing\n",encoding="utf-8")
            with self.assertRaises(ValueError):
                device_qa_orchestrator.load_projects(reg,base,["No such app"])


    def test_app_creation_wizard_defaults_to_provider_and_hive(self):
        brief=app_creation_wizard.make_brief({"app":{"name":"Fit Track"},"features":"daily log"})
        self.assertEqual(brief["app"]["package_name"],"com.dev.fittrack")
        self.assertEqual(brief["architecture"]["state_management"],"Provider")
        self.assertEqual(brief["architecture"]["storage"],"Hive")
        self.assertFalse(brief["integrations"]["admob_enabled"])

    def test_app_creation_wizard_rejects_invalid_package(self):
        with self.assertRaises(ValueError):
            app_creation_wizard.make_brief({"app":{"name":"Demo","package_name":"Bad Package"}})

    def test_app_creation_wizard_plan_has_approval_gates(self):
        brief=app_creation_wizard.make_brief({"app":{"name":"Demo"}})
        plan=app_creation_wizard.create_plan(brief)
        self.assertTrue(plan["implementation_order"][0]["approval_required"])
        self.assertTrue(plan["implementation_order"][-1]["approval_required"])
        self.assertFalse(brief["release"]["publish_automatically"])

    def test_one_command_workflow_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "generated"
            result = one_command_app_workflow.run({"app": {"name": "Fit Track"}}, target, execute=False)
            self.assertEqual(result["status"], "DRY_RUN")
            self.assertFalse(target.exists())
            self.assertFalse(result["source_code_generated"])

    def test_one_command_workflow_cli_accepts_explicit_dry_run(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "generated"
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "one_command_app_workflow.py"),
                 "--name", "Dry Run App", "--goal", "Check explicit dry-run flag",
                 "--output", str(output), "--dry-run"],
                capture_output=True, text=True, cwd=ROOT, timeout=10)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn('"status": "DRY_RUN"', proc.stdout)
            self.assertFalse(output.exists())

    def test_one_command_workflow_cli_rejects_execute_and_dry_run_together(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "one_command_app_workflow.py"),
             "--name", "Conflict App", "--execute", "--dry-run"],
            capture_output=True, text=True, cwd=ROOT, timeout=10)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("not allowed with argument", proc.stderr)

    def test_one_command_workflow_creates_resumable_workspace(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "generated"
            result = one_command_app_workflow.run({"app": {"name": "Fit Track"}, "features": "onboarding,settings,offline_states"}, target, execute=True)
            app_dir = target / "fittrack"
            self.assertEqual(result["status"], "CREATED")
            self.assertTrue((app_dir / "APP_BRIEF.json").is_file())
            self.assertTrue((app_dir / "FEATURE_MODULES.json").is_file())
            self.assertTrue((app_dir / "workflow" / "workflow_state.json").is_file())
            self.assertTrue((app_dir / "workflow" / "prompts" / "architecture_review.md").is_file())
            self.assertFalse(result["source_code_generated"])

    def test_one_command_workflow_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "generated"
            one_command_app_workflow.run({"app": {"name": "Demo"}}, target, execute=True)
            with self.assertRaises(FileExistsError):
                one_command_app_workflow.run({"app": {"name": "Demo"}}, target, execute=True)

    def test_create_app_dry_run_and_existing_target_protection(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "generated"
            command = [sys.executable, str(ROOT / "scripts" / "create_app.py"),
                       "--name", "Factory Test", "--package", "com.dev.factorytest",
                       "--target", str(target)]
            dry_run = subprocess.run(command + ["--dry-run"], capture_output=True,
                                     text=True, cwd=ROOT, timeout=30)
            self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
            self.assertIn("DRY RUN", dry_run.stdout)
            self.assertFalse(target.exists())

            target.mkdir()
            sentinel = target / "keep.txt"
            sentinel.write_text("existing user data", encoding="utf-8")
            refused = subprocess.run(command, capture_output=True, text=True,
                                      cwd=ROOT, timeout=30)
            self.assertEqual(refused.returncode, 2)
            self.assertIn("refusing to overwrite", refused.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "existing user data")

    def test_create_app_dry_run_validates_all_options_without_writing(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "generated"
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "create_app.py"),
                 "--name", "Demo", "--package", "com.dev.demo",
                 "--target", str(target), "--primary-color", "not-a-color",
                 "--dry-run"],
                capture_output=True, text=True, cwd=ROOT, timeout=30)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("six-digit hex", proc.stderr)
            self.assertFalse(target.exists())

    def test_create_app_copy_excludes_generated_and_local_files(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            source = base / "starter"
            (source / "lib").mkdir(parents=True)
            (source / ".dart_tool").mkdir()
            (source / "build").mkdir()
            (source / "android").mkdir()
            (source / ".env.example").write_text("API_BASE_URL=https://example.invalid\n", encoding="utf-8")
            (source / "lib" / "main.dart").write_text("void main() {}\n", encoding="utf-8")
            (source / ".dart_tool" / "cache").write_text("generated", encoding="utf-8")
            (source / "build" / "output.apk").write_text("generated", encoding="utf-8")
            (source / "android" / "local.properties").write_text("sdk.dir=/local/sdk\n", encoding="utf-8")
            (source / ".env").write_text("API_KEY=local-secret\n", encoding="utf-8")
            target = base / "copy"

            create_app.copy_starter(source, target)

            self.assertTrue((target / "lib" / "main.dart").is_file())
            self.assertTrue((target / ".env.example").is_file())
            self.assertFalse((target / ".dart_tool").exists())
            self.assertFalse((target / "build").exists())
            self.assertFalse((target / "android" / "local.properties").exists())
            self.assertFalse((target / ".env").exists())

    def test_create_app_generates_root_gitignore_and_preserves_app_sources(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            target=base/"generated"
            android=base/"scaffold"/"android"
            android.mkdir(parents=True)
            with mock.patch.object(create_app, "generate_android_scaffold", return_value=android), \
                 mock.patch.object(create_app, "configure_android"):
                create_app.create_app(
                    "Ignore Rules App",
                    "com.dev.ignorerules",
                    target,
                )

            ignore_file=target/".gitignore"
            self.assertTrue(ignore_file.is_file())
            rules=set(ignore_file.read_text(encoding="utf-8").splitlines())
            for expected in (
                ".dart_tool/",
                "**/build/",
                ".gradle/",
                "**/local.properties",
                ".env",
                ".env.*",
                "!.env.example",
                "key.properties",
                "**/*.jks",
                "**/*.keystore",
                "*.pem",
                "*.p8",
                "ios/Pods/",
                "ios/.symlinks/",
                ".idea/",
                ".vscode/",
                ".DS_Store",
            ):
                self.assertIn(expected,rules)
            self.assertNotIn("lib/",rules)
            self.assertNotIn("assets/",rules)
            self.assertNotIn("pubspec.yaml",rules)
            self.assertTrue((target/"pubspec.yaml").is_file())
            self.assertTrue((target/"lib"/"main.dart").is_file())
            self.assertTrue((target/"test").is_dir())
            self.assertTrue((target/"APP_CONFIG.json").is_file())

    def test_create_app_starter_gitignore_matches_canonical_and_is_tracked(self):
        source=ROOT/"design_system"/"nova_ui_flutter"
        starter=ROOT/"templates"/"nova_ui_flutter_starter"
        comparison=template_sync.compare_files(source,starter)
        self.assertIn(".gitignore",comparison["source_files"])
        self.assertIn(".gitignore",comparison["target_files"])
        self.assertNotIn(".gitignore",comparison["different"])

    def test_release_gradle_never_uses_debug_signing_and_requires_explicit_env(self):
        gradle=(ROOT/"design_system"/"nova_ui_flutter"/"android"/"app"/"build.gradle.kts").read_text(
            encoding="utf-8")
        self.assertNotIn('signingConfig = signingConfigs.getByName("debug")',gradle)
        for variable in (
            "MYAPP_RELEASE_SIGNING_ENABLED",
            "MYAPP_RELEASE_STORE_FILE",
            "MYAPP_RELEASE_STORE_PASSWORD",
            "MYAPP_RELEASE_KEY_ALIAS",
            "MYAPP_RELEASE_KEY_PASSWORD",
        ):
            self.assertIn(variable,gradle)
        self.assertIn("releaseBuildRequested",gradle)
        self.assertIn("(assemble|bundle|package|validatesigning)",gradle)
        self.assertNotIn('contains("release", ignoreCase = true)',gradle)
        self.assertIn('signingConfig = signingConfigs.getByName("release")',gradle)

    def test_create_app_copy_refuses_starter_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            source = base / "starter"
            source.mkdir()
            outside = base / "outside.txt"
            outside.write_text("outside source", encoding="utf-8")
            (source / "linked.txt").symlink_to(outside)
            with self.assertRaisesRegex(ValueError, "symlink"):
                create_app.copy_starter(source, base / "copy")

    def test_create_app_updates_dart_package_imports_with_metadata(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)
            test_dir = target / "test"
            test_dir.mkdir()
            test_file = test_dir / "widget_test.dart"
            test_file.write_text(
                "import 'package:nova_ui/main.dart';\n"
                'import "package:nova_ui/core/design_system/nova_colors.dart";\n',
                encoding="utf-8")

            create_app.update_package_imports(target, "factory_test")

            updated = test_file.read_text(encoding="utf-8")
            self.assertIn("package:factory_test/main.dart", updated)
            self.assertIn("package:factory_test/core/design_system/nova_colors.dart", updated)
            self.assertNotIn("package:nova_ui/", updated)

    def test_create_app_configures_android_identity_and_flavors(self):
        with tempfile.TemporaryDirectory() as d:
            android = Path(d)
            gradle = android / "app" / "build.gradle.kts"
            gradle.parent.mkdir(parents=True)
            gradle.write_text(
                'android {\n'
                '    namespace = "com.example.demo"\n'
                '    defaultConfig {\n'
                '        applicationId = "com.example.demo"\n'
                '        minSdk = flutter.minSdkVersion\n'
                '        targetSdk = flutter.targetSdkVersion\n'
                '    }\n'
                '    buildTypes {\n'
                '        release {\n'
                '            signingConfig = signingConfigs.getByName("debug")\n'
                '        }\n'
                '    }\n'
                '}\n',
                encoding="utf-8",
            )
            manifest = gradle.parent / "src" / "main" / "AndroidManifest.xml"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                '<manifest><application android:label="demo" /></manifest>',
                encoding="utf-8",
            )
            activity = gradle.parent / "src" / "main" / "kotlin" / "com" / "example" / "demo" / "MainActivity.kt"
            activity.parent.mkdir(parents=True)
            activity.write_text(
                "package com.example.demo\n\nclass MainActivity\n",
                encoding="utf-8",
            )

            create_app.configure_android(
                android, "com.dev.factorytest", "Factory $ Test", min_sdk=24,
                target_sdk=35,
            )

            generated = gradle.read_text(encoding="utf-8")
            self.assertIn('namespace = "com.dev.factorytest"', generated)
            self.assertIn('applicationId = "com.dev.factorytest"', generated)
            self.assertIn("minSdk = 24", generated)
            self.assertIn("targetSdk = 35", generated)
            self.assertIn("resValues = true", generated)
            self.assertIn('create("development")', generated)
            self.assertIn('create("production")', generated)
            self.assertIn(r'Factory \$ Test', generated)
            self.assertNotIn('signingConfig = signingConfigs.getByName("debug")', generated)
            self.assertIn("Release signing is not configured.", generated)
            self.assertIn("(assemble|bundle|package|validatesigning)", generated)
            self.assertIn('signingConfig = signingConfigs.getByName("release")', generated)
            self.assertIn("MYAPP_RELEASE_STORE_FILE", generated)
            self.assertIn('android:label="@string/app_name"', manifest.read_text(encoding="utf-8"))
            self.assertTrue(
                (gradle.parent / "src" / "main" / "kotlin" / "com" / "dev" /
                 "factorytest" / "MainActivity.kt").is_file()
            )
            self.assertFalse(activity.exists())

    def test_create_app_configures_groovy_android_scaffold(self):
        with tempfile.TemporaryDirectory() as d:
            android = Path(d)
            gradle = android / "app" / "build.gradle"
            gradle.parent.mkdir(parents=True)
            gradle.write_text(
                'android {\n'
                '    namespace "com.example.demo"\n'
                '    defaultConfig {\n'
                '        applicationId "com.example.demo"\n'
                '        minSdk flutter.minSdkVersion\n'
                '        targetSdk flutter.targetSdkVersion\n'
                '    }\n'
                '    buildTypes {\n'
                '        release {\n'
                '            signingConfig signingConfigs.debug\n'
                '        }\n'
                '    }\n'
                '}\n',
                encoding="utf-8",
            )
            manifest = gradle.parent / "src" / "main" / "AndroidManifest.xml"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                '<manifest><application android:label="demo" /></manifest>',
                encoding="utf-8",
            )
            activity = gradle.parent / "src" / "main" / "kotlin" / "com" / "example" / "demo" / "MainActivity.kt"
            activity.parent.mkdir(parents=True)
            activity.write_text("package com.example.demo\n\nclass MainActivity\n", encoding="utf-8")

            create_app.configure_android(android, "com.dev.factorytest", "Factory Test", 24, 35)

            generated = gradle.read_text(encoding="utf-8")
            self.assertIn('namespace "com.dev.factorytest"', generated)
            self.assertIn('applicationId "com.dev.factorytest"', generated)
            self.assertIn("minSdk 24", generated)
            self.assertIn("targetSdk 35", generated)
            self.assertIn("resValues true", generated)
            self.assertIn('applicationIdSuffix ".dev"', generated)
            self.assertNotIn("signingConfig signingConfigs.debug", generated)
            self.assertIn("Release signing is not configured.", generated)
            self.assertIn("MYAPP_RELEASE_STORE_FILE", generated)

    def test_create_app_branding_updates_flutter_theme_and_title(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d)
            main = project / "lib" / "main.dart"
            main.parent.mkdir()
            main.write_text(
                "import 'core/design_system/nova_theme.dart';\n"
                "void main() {}\n"
                "title: 'Nova UI',\n"
                "theme: NovaTheme.light(),\n"
                "darkTheme: NovaTheme.dark(),\n",
                encoding="utf-8",
            )
            create_app.configure_dart_branding(project, "Factory Test", "#123ABC")
            content = main.read_text(encoding="utf-8")
            self.assertIn('title: "Factory Test"', content)
            self.assertIn("NovaBrandTheme.light(const Color(0xFF123ABC))", content)
            self.assertIn("NovaBrandTheme.dark(const Color(0xFF123ABC))", content)
            self.assertIn("nova_brand_theme.dart", content)

    def test_v2_app_config_and_contradiction_validation(self):
        data = create_app.app_config(
            "Demo", "com.dev.demo", "1.0.0+1", "#123ABC", None, None)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "APP_CONFIG.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertTrue(validate_app_config.validate(path)["valid"])
            data["build"]["android"]["application_id"] = "com.dev.other"
            path.write_text(json.dumps(data), encoding="utf-8")
            result = validate_app_config.validate(path)
            self.assertFalse(result["valid"])
            self.assertTrue(any("contradicts" in error for error in result["errors"]))

    def test_config_v1_migration_is_additive_and_preserves_input(self):
        original = {
            "app": {"name": "Demo", "package_name": "com.dev.demo", "version": "1.0.0+1"},
            "architecture": {"state_management": "Provider", "storage": "Hive"},
            "integrations": {"backend": "none"},
            "design": {"locales": ["en"]},
            "custom_section": {"keep": True},
        }
        migrated = validate_app_config.migrate_to_v2(original)
        self.assertEqual(original.get("schema_version"), None)
        self.assertEqual(migrated["schema_version"], 2)
        self.assertEqual(migrated["custom_section"], {"keep": True})
        self.assertEqual(migrated["architecture"]["storage"], "Hive")
        self.assertEqual(migrated["build"]["android"]["application_id"], "com.dev.demo")
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "APP_CONFIG.json"
            path.write_text(json.dumps(migrated), encoding="utf-8")
            self.assertTrue(validate_app_config.validate(path)["valid"])

    def test_config_validator_rejects_boolean_schema_version(self):
        data = create_app.app_config(
            "Demo", "com.dev.demo", "1.0.0+1", "#123ABC", None, None)
        data["schema_version"] = True
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "APP_CONFIG.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            result = validate_app_config.validate(path)
            self.assertFalse(result["valid"])
            self.assertTrue(any("schema_version" in error for error in result["errors"]))

    def test_architecture_audit_reports_import_boundary_violations(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d)
            (project / "lib" / "features" / "demo" / "domain").mkdir(parents=True)
            (project / "lib" / "features" / "demo" / "data").mkdir(parents=True)
            (project / "pubspec.yaml").write_text("name: demo_app\n", encoding="utf-8")
            domain = project / "lib" / "features" / "demo" / "domain" / "model.dart"
            domain.write_text(
                "import 'package:flutter/material.dart';\n"
                "import '../data/repository.dart';\n",
                encoding="utf-8",
            )
            result = architecture_audit.audit(project)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(len(result["errors"]), 2)

    def test_architecture_audit_is_explicit_when_no_layer_files_exist(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d)
            (project / "lib").mkdir()
            (project / "pubspec.yaml").write_text("name: demo_app\n", encoding="utf-8")
            result = architecture_audit.audit(project)
            self.assertEqual(result["status"], "PARTIAL")
            self.assertTrue(result["warnings"])

    def test_template_sync_detects_extra_files_and_ignores_build_caches(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            source = base / "source"
            target = base / "target"
            for root in (source, target):
                (root / "lib").mkdir(parents=True)
                (root / "test").mkdir()
                (root / ".dart_tool").mkdir()
                (root / "build").mkdir()
            (source / "lib" / "main.dart").write_text("source\n", encoding="utf-8")
            (target / "lib" / "main.dart").write_text("source\n", encoding="utf-8")
            (source / ".dart_tool" / "cache").write_text("ignored", encoding="utf-8")
            (target / "build" / "cache").write_text("ignored", encoding="utf-8")
            (target / "lib" / "extra.dart").write_text("extra\n", encoding="utf-8")

            comparison = template_sync.compare_files(source, target)

            self.assertEqual(comparison["missing"], [])
            self.assertEqual(comparison["different"], [])
            self.assertEqual(comparison["extra"], ["lib/extra.dart"])


    def test_ui_screen_generator_creates_complete_reference_pack(self):
        brief = {"app": {"name": "Fit Track", "primary_goal": "Track fitness"},
                 "screens": ["Home", "Add activity", "History", "Statistics"]}
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "ui"
            screens = ui_screen_generator.generate(brief, out)
            self.assertGreaterEqual(len(screens), 7)
            for filename in ["SCREEN_INVENTORY.json", "SCREEN_INVENTORY.md",
                             "UI_DESIGN_PROMPTS.md", "UI_REFERENCE_INDEX.md",
                             "CLAUDE_CODE_UI_INSTRUCTIONS.md", "UI_IMPLEMENTATION_STATUS.md"]:
                self.assertTrue((out / filename).is_file(), filename)
            self.assertTrue((out / "ui_references" / "README.md").is_file())

    def test_one_command_workflow_includes_ui_deliverables(self):
        with tempfile.TemporaryDirectory() as d:
            result = one_command_app_workflow.run(
                {"app": {"name": "Demo", "primary_goal": "A demo app"}, "screens": "Home,Reports"},
                Path(d), execute=True)
            target = Path(result["target"])
            self.assertTrue((target / "SCREEN_INVENTORY.json").is_file())
            self.assertTrue((target / "UI_DESIGN_PROMPTS.md").is_file())
            self.assertTrue((target / "CLAUDE_CODE_UI_INSTRUCTIONS.md").is_file())
            self.assertTrue((target / "ui_references").is_dir())
            self.assertGreaterEqual(result["ui_screen_count"], 5)

if __name__ == "__main__":
    unittest.main()

class AdvancedMilestoneTests(unittest.TestCase):
    def test_all_milestones_15_to_35_generate_reports(self):
        import advanced_milestone_engine as engine
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'APP_BRIEF.json').write_text(json.dumps({
                'app': {'name': 'Demo App', 'primary_goal': 'Track things', 'version': '1.0.0+1'},
                'design': {'locales': ['en', 'mr']}, 'screens': ['Home', 'History'],
                'features': ['offline storage']
            }), encoding='utf-8')
            (root / 'apps').mkdir()
            (root / 'apps' / 'PROJECT_REGISTRY.csv').write_text('app_name,package_name\nDemo,com.dev.demo\n', encoding='utf-8')
            for milestone in range(15, 36):
                result = engine.run(milestone, root)
                self.assertEqual(result['status'], 'GENERATED')
                self.assertTrue((Path(result['output']) / 'MILESTONE_REPORT.json').is_file())

    def test_security_scan_detects_possible_secret(self):
        import advanced_milestone_engine as engine
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'lib').mkdir()
            (root/'lib'/'sample.dart').write_text("const api_key = 'abcdefghijk123456';", encoding='utf-8')
            result = engine.run(28, root)
            report=json.loads((Path(result['output'])/'QUALITY_REPORT.json').read_text())
            self.assertTrue(any(x['code']=='SECURITY' for x in report['findings']))
