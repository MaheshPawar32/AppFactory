"""V4.0 Batch 3: shared core + milestones 41–44."""
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from factory_fixtures import ROOT, make_ctx, make_flutter_app, write_registry

from myappfactory import approvals as A
from myappfactory import audit, context, redact, reports as R, runner
from myappfactory import auth_qa, data_readiness, privacy, secrets_manager as S
from myappfactory.cli import main as cli_main

FAKE_GOOGLE = "AIza" + "B" * 35
FAKE_ANTHROPIC = "sk-ant-" + "x" * 30


class Tmp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.state = self.base / "state"

    def tearDown(self):
        self._tmp.cleanup()


class RedactionTests(unittest.TestCase):
    def test_redacts_patterns_known_values_and_env(self):
        text = f'key={FAKE_GOOGLE} anth={FAKE_ANTHROPIC} password: "hunter2hunter" custom=TopSecretValue1'
        out = redact.redact(text, extra_values=["TopSecretValue1"], environ={"MY_TOKEN": "envtokenvalue"})
        for secret in (FAKE_GOOGLE, FAKE_ANTHROPIC, "hunter2hunter", "TopSecretValue1"):
            self.assertNotIn(secret, out)
        self.assertIn("password", out)
        self.assertEqual(redact.redact("token envtokenvalue", environ={"MY_TOKEN": "envtokenvalue"}),
                         "token [REDACTED]")

    def test_private_key_block_and_jwt(self):
        text = "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n" \
               "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        out = redact.redact(text, environ={})
        self.assertNotIn("abc", out)
        self.assertNotIn("eyJzdWIi", out)

    def test_find_secrets_reports_lines_not_values(self):
        hits = list(redact.find_secrets(f"a\nb\nkey = '{FAKE_GOOGLE}'\n"))
        self.assertEqual(hits, [("google_api_key", 3)])


class ContextIsolationTests(Tmp):
    def test_resolve_rejects_escape_and_symlink(self):
        a = make_flutter_app(self.base, "app_a")
        b = make_flutter_app(self.base, "app_b")
        ctx = make_ctx(a, self.state)
        self.assertEqual(ctx.resolve("lib/main.dart"), (a / "lib/main.dart").resolve())
        with self.assertRaises(context.IsolationError):
            ctx.resolve("../app_b/lib/main.dart")
        (a / "link").symlink_to(b)
        with self.assertRaises(context.IsolationError):
            ctx.resolve("link/lib/main.dart")
        with self.assertRaises(context.IsolationError):
            ctx.state_path("..", "com.test.app_b", "x")

    def test_registry_rejects_duplicates_and_overlapping_roots(self):
        a = make_flutter_app(self.base, "app_a")
        reg = self.base / "reg.csv"
        write_registry(reg, [{"app_name": "A", "package_name": "com.a.one", "project_path": str(a)},
                             {"app_name": "A2", "package_name": "com.a.one", "project_path": str(self.base / "x")}])
        with self.assertRaises(context.RegistryError):
            context.load_registered_apps(reg, self.base, self.state)
        write_registry(reg, [{"app_name": "A", "package_name": "com.a.one", "project_path": str(a)},
                             {"app_name": "Nested", "package_name": "com.a.two", "project_path": str(a / "lib")}])
        with self.assertRaises(context.RegistryError):
            context.load_registered_apps(reg, self.base, self.state)

    def test_resolve_app_prefers_registry_and_supports_adhoc(self):
        a = make_flutter_app(self.base, "app_a", package="com.reg.app")
        reg = self.base / "reg.csv"
        write_registry(reg, [{"app_name": "Registered", "package_name": "com.reg.app", "project_path": str(a)}])
        ctx = context.resolve_app(project=a, registry=reg, state_root=self.state)
        self.assertTrue(ctx.registered)
        self.assertEqual(ctx.app_id, "com.reg.app")
        other = make_flutter_app(self.base, "app_c", package="com.adhoc.c")
        adhoc = context.resolve_app(project=other, registry=reg, state_root=self.state)
        self.assertFalse(adhoc.registered)
        self.assertEqual(adhoc.app_id, "com.adhoc.c")
        with self.assertRaises(context.RegistryError):
            context.get_app("com.missing.app", reg, self.base, self.state)


class AuditAndApprovalTests(Tmp):
    def test_audit_chain_detects_tampering(self):
        log = audit.AuditLog(self.base / "a.jsonl")
        log.append("one", "me", {"password": "should-not-leak-123"})
        log.append("two", "me")
        self.assertEqual(log.verify(), (True, None))
        self.assertNotIn("should-not-leak-123", (self.base / "a.jsonl").read_text())
        lines = (self.base / "a.jsonl").read_text().splitlines()
        tampered = json.loads(lines[0])
        tampered["actor"] = "attacker"
        (self.base / "a.jsonl").write_text(json.dumps(tampered) + "\n" + lines[1] + "\n")
        self.assertEqual(log.verify(), (False, 1))

    def test_approval_is_payload_bound_single_use_and_human_only(self):
        store = A.ApprovalStore(self.base / "s", "com.x.y")
        payload = {"artifact": "app.aab", "sha256": "abc"}
        with self.assertRaises(A.ApprovalRequired) as raised:
            store.require("play_upload", payload)
        request_id = raised.exception.request["id"]
        with self.assertRaises(A.ApprovalError):
            store.decide(request_id, "agent", True)
        with self.assertRaises(A.ApprovalRequired):  # still pending, not approved
            store.require("play_upload", payload)
        store.decide(request_id, "Asha", True, "checked")
        with self.assertRaises(A.ApprovalRequired):  # different payload is not covered
            store.require("play_upload", {"artifact": "other.aab", "sha256": "def"})
        self.assertEqual(store.require("play_upload", payload)["status"], "CONSUMED")
        with self.assertRaises(A.ApprovalRequired):  # single use
            store.require("play_upload", payload)

    def test_approval_expiry_and_unknown_action(self):
        store = A.ApprovalStore(self.base / "s", "scope")
        item = store.request("play_upload", {"a": 1}, ttl_hours=-1)
        self.assertEqual(store.get(item["id"])["status"], "EXPIRED")
        with self.assertRaises(A.ApprovalError):
            store.decide(item["id"], "Asha", True)
        with self.assertRaises(A.ApprovalError):
            store.request("launch_missiles", {})

    def test_approvals_are_isolated_per_app(self):
        a = make_ctx(make_flutter_app(self.base, "app_a"), self.state)
        b = make_ctx(make_flutter_app(self.base, "app_b"), self.state)
        payload = {"x": 1}
        item = A.ApprovalStore.for_app(a).request("database_migration", payload)
        A.ApprovalStore.for_app(a).decide(item["id"], "Asha", True)
        with self.assertRaises(A.ApprovalRequired):
            A.ApprovalStore.for_app(b).require("database_migration", payload)
        with self.assertRaises(A.ApprovalError):
            A.ApprovalStore.for_app(b).decide(item["id"], "Asha", True)


class RunnerAndReportTests(Tmp):
    def test_runner_rejects_strings_and_unlisted_executables(self):
        with self.assertRaises(runner.CommandRejected):
            runner.run("flutter test", self.base)
        with self.assertRaises(runner.CommandRejected):
            runner.run(["rm", "-rf", "/"], self.base)
        with self.assertRaises(runner.CommandRejected):
            runner.run(["bash", "-c", "echo hi"], self.base)

    def test_runner_timeout_cancel_and_redaction(self):
        allowed = runner.ALLOWED_EXECUTABLES | {Path(sys.executable).name}
        result = runner.run([sys.executable, "-c", "import time; time.sleep(5)"], self.base, timeout=1, allowed=allowed)
        self.assertTrue(result.timed_out)
        self.assertEqual(result.status, "FAIL")
        cancel = threading.Event()
        threading.Timer(0.3, cancel.set).start()
        result = runner.run([sys.executable, "-c", "import time; time.sleep(5)"], self.base, timeout=30,
                            cancel_event=cancel, allowed=allowed)
        self.assertTrue(result.cancelled)
        result = runner.run([sys.executable, "-c", "import os; print(os.environ['MYAPP_X_PASSWORD'])"], self.base,
                            env_extra={"MYAPP_X_PASSWORD": "s3cretvalue"}, allowed=allowed)
        self.assertTrue(result.ok)
        self.assertNotIn("s3cretvalue", result.stdout)

    def test_missing_working_directory_is_rejected_not_reported_as_missing_tool(self):
        with self.assertRaises(runner.CommandRejected):
            runner.run(["adb", "devices"], self.base / "does-not-exist")

    def test_missing_executable_is_not_run_not_pass(self):
        with mock.patch.object(runner, "which", return_value=None):
            result = runner.run(["osv-scanner", "--version"], self.base)
        self.assertEqual(result.status, "NOT RUN")

    def test_reports_rollup_identity_and_no_overwrite(self):
        ctx = make_ctx(make_flutter_app(self.base, "app_a"), self.state)
        other = make_ctx(make_flutter_app(self.base, "app_b"), self.state)
        self.assertEqual(R.rollup([R.check("a", R.PASS), R.check("b", R.NOT_APPLICABLE)]), R.PASS)
        self.assertEqual(R.rollup([R.check("a", R.PASS), R.check("b", R.NOT_RUN)]), R.PARTIAL)
        self.assertEqual(R.rollup([R.check("a", R.PASS), R.check("b", R.BLOCKED)]), R.FAIL)
        self.assertEqual(R.rollup([]), R.NOT_RUN)
        with self.assertRaises(ValueError):
            R.check("x", "GREAT")
        report = R.make_report(ctx, "demo", "Demo", [R.check("a", R.PASS, f"key {FAKE_GOOGLE}")])
        path = R.write_report(ctx, report, name="fixed")
        self.assertNotIn(FAKE_GOOGLE, path.read_text())
        with self.assertRaises(FileExistsError):
            R.write_report(ctx, report, name="fixed")
        with self.assertRaises(PermissionError):
            R.write_report(other, report)
        self.assertEqual(R.latest_report(ctx, "demo")["app"]["app_id"], ctx.app_id)
        self.assertIsNone(R.latest_report(other, "demo"))


class SecretsTests(Tmp):
    def _app(self, **kw):
        root = make_flutter_app(self.base, kw.pop("name", "app_a"), **kw)
        return make_ctx(root, self.state)

    def test_store_permissions_values_never_in_reports(self):
        ctx = self._app(config={"secrets": [{"name": "API_TOKEN", "environments": ["development"]}]})
        store = S.SecretStore(ctx)
        store.set("development", "API_TOKEN", "dev-value-12345")
        self.assertEqual(stat.S_IMODE(store.directory.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((store.directory / "development.json").stat().st_mode), 0o600)
        report = S.validate(ctx, "development", environ={})
        self.assertEqual(report["status"], R.PASS)
        self.assertNotIn("dev-value-12345", json.dumps(report))
        self.assertNotIn("dev-value-12345", (ctx.state_dir / "audit.log.jsonl").read_text())
        os.chmod(store.directory / "development.json", 0o644)
        self.assertEqual(S.validate(ctx, "development", environ={})["status"], R.FAIL)

    def test_store_refuses_location_inside_app_tree(self):
        root = make_flutter_app(self.base, "app_a")
        ctx = make_ctx(root, root / ".factory_state")
        with self.assertRaises(context.IsolationError):
            S.SecretStore(ctx)

    def test_missing_required_and_production_signing(self):
        ctx = self._app()
        report = S.validate(ctx, "production", environ={})
        self.assertEqual(report["status"], R.FAIL)
        missing = {c["check"] for c in report["checks"] if c["status"] == R.FAIL}
        self.assertIn("Secret MYAPP_RELEASE_STORE_PASSWORD", missing)
        self.assertEqual(S.validate(ctx, "development", environ={})["status"], R.PASS)

    def test_keystore_inside_project_is_rejected(self):
        ctx = self._app()
        keystore = ctx.root / "android" / "upload.jks"
        keystore.write_bytes(b"x")
        env = {S.scoped_env_name(ctx, "production", n): "value-123456" for n in S.RELEASE_SIGNING_VARS}
        env[S.scoped_env_name(ctx, "production", "MYAPP_RELEASE_STORE_FILE")] = str(keystore)
        checks = {c["check"]: c for c in S.validate(ctx, "production", environ=env)["checks"]}
        self.assertEqual(checks["Secret MYAPP_RELEASE_STORE_FILE"]["status"], R.FAIL)

    def test_lookup_is_app_scoped(self):
        a, b = self._app(name="app_a"), self._app(name="app_b")
        S.SecretStore(a).set("development", "API_TOKEN", "a-secret-value")
        self.assertEqual(S.lookup(a, "development", "API_TOKEN", environ={})[0], "a-secret-value")
        self.assertEqual(S.lookup(b, "development", "API_TOKEN", environ={}), (None, None))
        env = {S.scoped_env_name(a, "development", "API_TOKEN"): "env-a", "API_TOKEN": "plain"}
        self.assertEqual(S.lookup(b, "development", "API_TOKEN", environ=env), (None, None))
        self.assertEqual(S.lookup(b, "development", "API_TOKEN", environ={**env, "CI": "true"})[1], "ci-env:API_TOKEN")
        with self.assertRaises(S.MissingSecret):
            S.env_for_process(b, "development", ["API_TOKEN", "OTHER"], environ={})

    def test_exposure_scan_finds_secrets_signing_files_and_gitignore_gaps(self):
        ctx = self._app(files={
            "lib/config.dart": f"const k = '{FAKE_ANTHROPIC}';\n"
                               "const t = String.fromEnvironment('API_TOKEN', defaultValue: 'abc123secret');\n",
            "android/app/google-services.json": f'{{"current_key": "{FAKE_GOOGLE}"}}',
            "android/key.properties": "storePassword=x",
            "build/leak.dart": f"'{FAKE_ANTHROPIC}'"}, gitignore=False)
        report = S.scan_exposure(ctx)
        checks = {c["check"]: c["status"] for c in report["checks"]}
        self.assertEqual(checks["Secret-shaped values in source"], R.FAIL)
        self.assertEqual(checks["Signing material in project tree"], R.FAIL)
        self.assertEqual(checks[".gitignore secret coverage"], R.FAIL)
        self.assertEqual(checks["Client configuration API keys"], R.WARN)
        files = {f["file"] for f in report["data"]["findings"]}
        self.assertEqual(files, {"lib/config.dart"})  # build/ skipped
        self.assertNotIn(FAKE_ANTHROPIC, json.dumps(report))

    def test_ci_template_has_names_only(self):
        ctx = self._app(config={"secrets": [{"name": "API_TOKEN"}]})
        S.SecretStore(ctx).set("production", "API_TOKEN", "never-printed-1")
        template = S.ci_template(ctx, "production")
        self.assertIn("API_TOKEN: ${{ secrets.API_TOKEN }}", template)
        self.assertIn("MYAPP_RELEASE_KEY_PASSWORD", template)
        self.assertNotIn("never-printed-1", template)

    def test_rotation_overdue_warns(self):
        ctx = self._app(config={"secrets": [{"name": "API_TOKEN", "rotation_days": 30}]})
        store = S.SecretStore(ctx)
        store.set("development", "API_TOKEN", "value-123456")
        meta = json.loads((store.directory / "meta.json").read_text())
        meta["development"]["API_TOKEN"]["rotated_at"] = "2020-01-01T00:00:00+00:00"
        store._write(store.directory / "meta.json", meta)
        check = next(c for c in S.validate(ctx, "development", environ={})["checks"] if "API_TOKEN" in c["check"])
        self.assertEqual(check["status"], R.WARN)


class AuthTests(Tmp):
    def test_offline_app_is_not_applicable(self):
        ctx = make_ctx(make_flutter_app(self.base, "app_a", deps=["hive"]), self.state)
        report = auth_qa.run_auth_qa(ctx)
        self.assertEqual(report["status"], R.PASS)
        self.assertEqual(report["checks"][0]["status"], R.NOT_APPLICABLE)

    def test_static_issues_and_test_discovery(self):
        ctx = make_ctx(make_flutter_app(self.base, "app_a", deps=["firebase_auth", "shared_preferences"], files={
            "lib/auth.dart": "void f(prefs, t){ prefs.setString('auth_token', t); print('id_token $t');\n"
                             "final u = 'http://api.example.com/login'; }\n",
            "test/login_test.dart": "void main(){ test('login succeeds', (){}); test('logout clears', (){}); }",
        }, config={"integrations": {"authentication": {"enabled": True, "provider": "firebase"}}}), self.state)
        report = auth_qa.run_auth_qa(ctx)
        rules = {i["rule"] for i in report["data"]["token_issues"]}
        self.assertEqual(rules, {"token_in_shared_preferences", "token_logged", "insecure_http"})
        checks = {c["check"]: c["status"] for c in report["checks"]}
        self.assertEqual(checks["Test coverage: login"], R.PASS)
        self.assertEqual(checks["Test coverage: roles"], R.NOT_RUN)
        self.assertEqual(checks["Secure token storage"], R.WARN)
        self.assertEqual(checks["Live provider checks"], R.NOT_RUN)
        self.assertEqual(report["status"], R.FAIL)

    def test_declared_auth_without_package_fails(self):
        ctx = make_ctx(make_flutter_app(self.base, "app_a", config={
            "integrations": {"authentication": {"enabled": True}}}), self.state)
        self.assertEqual(auth_qa.run_auth_qa(ctx)["checks"][0]["status"], R.FAIL)

    def test_supabase_live_adapter_with_fake_transport(self):
        calls = []

        class Resp(io.BytesIO):
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def opener(request, timeout):
            calls.append(request.full_url)
            body = json.loads(request.data or b"{}") if request.data else {}
            if request.full_url.endswith("/user"):
                raise auth_qa.urllib.error.HTTPError(request.full_url, 401, "no", {}, None)
            if body.get("password") == "pw-correct":
                return Resp(json.dumps({"access_token": "t", "expires_in": 3600}).encode())
            raise auth_qa.urllib.error.HTTPError(request.full_url, 400, "bad", {}, None)

        result = auth_qa.supabase_live_check("https://x.supabase.co", "anon", "a@b.c", "pw-correct", opener)
        self.assertEqual(result, {"login": True, "token_expiry_seconds": 3600, "rejects_bad_password": True,
                                  "rejects_unauthenticated_user_endpoint": True})
        self.assertEqual(len(calls), 3)

    def test_live_checks_not_run_without_credentials(self):
        ctx = make_ctx(make_flutter_app(self.base, "app_a", deps=["supabase_flutter"], config={
            "integrations": {"authentication": {"enabled": True}}}), self.state)
        with mock.patch.object(auth_qa, "run") as fake_run:
            report = auth_qa.run_auth_qa(ctx, execute=True, opener=lambda *a, **k: self.fail("no network"))
        fake_run.assert_not_called()  # no auth test files to run
        live = next(c for c in report["checks"] if c["check"] == "Supabase live check")
        self.assertEqual(live["status"], R.NOT_RUN)


HIVE_V1 = """
@HiveType(typeId: 1)
class Note {
  @HiveField(0) final String id;
  @HiveField(1) final String title;
}
"""
HIVE_V2_REUSED = """
@HiveType(typeId: 1)
class Note {
  @HiveField(0) final String id;
  @HiveField(1) final String body;
}
"""


class DataReadinessTests(Tmp):
    def test_hive_schema_snapshot_and_unsafe_field_reuse(self):
        root = make_flutter_app(self.base, "app_a", deps=["hive"], files={"lib/note.dart": HIVE_V1})
        ctx = make_ctx(root, self.state)
        first = data_readiness.run_data_readiness(ctx, update_snapshot=True)
        self.assertEqual(first["data"]["schema"]["hive_types"]["Note"]["fields"], {"0": "id", "1": "title"})
        (root / "lib/note.dart").write_text(HIVE_V2_REUSED)
        second = data_readiness.run_data_readiness(ctx)
        check = next(c for c in second["checks"] if c["check"] == "Migration safety vs last snapshot")
        self.assertEqual(check["status"], R.FAIL)
        self.assertIn("reused", check["detail"])

    def test_duplicate_hive_ids_and_sqlite_version_without_upgrade(self):
        source = HIVE_V1 + "\n@HiveType(typeId: 1)\nclass Tag {\n  @HiveField(0) final String a;\n  @HiveField(0) final String b;\n}\n" \
                 "Future f() => openDatabase('x.db', version: 2, onCreate: (db, v) {});\n"
        ctx = make_ctx(make_flutter_app(self.base, "app_a", deps=["hive", "sqflite"], files={"lib/db.dart": source}), self.state)
        report = data_readiness.run_data_readiness(ctx)
        statuses = {c["check"]: c for c in report["checks"]}
        self.assertEqual(statuses["Schema definitions"]["status"], R.FAIL)
        self.assertIn("typeId 1 reused", statuses["Schema definitions"]["detail"])
        self.assertTrue(any(k.startswith("SQLite migration") and v["status"] == R.FAIL for k, v in statuses.items()))

    def test_sqlite_table_change_requires_version_bump(self):
        prev = {"sqlite_tables": {"notes": {"columns": ["id", "title"]}},
                "sqlite_databases": [{"file": "lib/db.dart", "version": 1}]}
        cur = {"hive_types": {}, "sqlite_tables": {"notes": {"columns": ["id"]}},
               "sqlite_databases": [{"file": "lib/db.dart", "version": 1}]}
        self.assertEqual(data_readiness.diff_schema(prev, cur)[0]["severity"], "high")
        cur["sqlite_databases"][0]["version"] = 2
        self.assertEqual(data_readiness.diff_schema(prev, cur), [])

    def test_offline_heuristic_and_test_discovery(self):
        ctx = make_ctx(make_flutter_app(self.base, "app_a", deps=["http", "hive"], files={
            "lib/api.dart": "import 'package:http/http.dart' as http;\nf() => http.get(Uri.parse('https://x'));\n",
            "lib/safe.dart": "f() async { try { await http.get(u); } on SocketException { } }\n",
            "test/repository_test.dart": "main(){ test('persists notes across restart', (){}); }\n",
        }), self.state)
        report = data_readiness.run_data_readiness(ctx)
        self.assertEqual([i["file"] for i in report["data"]["offline_issues"]], ["lib/api.dart"])
        self.assertEqual(report["data"]["tests"]["persistence"], ["test/repository_test.dart"])

    def test_no_storage_is_not_applicable(self):
        ctx = make_ctx(make_flutter_app(self.base, "app_a"), self.state)
        report = data_readiness.run_data_readiness(ctx)
        self.assertEqual(report["checks"][0]["status"], R.NOT_APPLICABLE)

    def test_device_workflows_enforce_isolation_and_approval(self):
        ctx = make_ctx(make_flutter_app(self.base, "app_a"), self.state, package="com.test.app_a")
        with self.assertRaises(context.IsolationError):
            data_readiness.backup_device_data(ctx, "com.other.app")
        with self.assertRaises(context.IsolationError):
            data_readiness.simulate_offline_launch(ctx, "com.other.app")
        archive = ctx.state_path("data", "device_backups", "x.tar")
        archive.parent.mkdir(parents=True)
        archive.write_bytes(b"")
        with mock.patch.object(data_readiness, "run_binary") as fake:
            with self.assertRaises(A.ApprovalRequired):
                data_readiness.restore_device_data(ctx, "com.test.app_a", archive)
            fake.assert_not_called()
        with self.assertRaises(context.IsolationError):
            data_readiness.restore_device_data(ctx, "com.test.app_a", self.base / "elsewhere.tar")

    def test_offline_simulation_always_restores_connectivity(self):
        ctx = make_ctx(make_flutter_app(self.base, "app_a"), self.state, package="com.test.app_a")
        commands = []

        def fake_run(cmd, cwd, timeout=600, **kw):
            commands.append(cmd)
            if "monkey" in cmd:
                raise RuntimeError("device vanished")
            return runner.CommandResult(cmd, str(cwd), 0)

        self.assertFalse(ctx.state_dir.exists())
        with mock.patch.object(data_readiness, "run", side_effect=fake_run), \
                mock.patch.object(data_readiness.time, "sleep"):
            with self.assertRaises(RuntimeError):
                data_readiness.simulate_offline_launch(ctx, "com.test.app_a")
        self.assertIn("disable", commands[-1])
        self.assertTrue(ctx.state_dir.is_dir())  # created so device commands have a valid cwd


class PrivacyTests(Tmp):
    def test_inventory_inference_and_missing_declarations(self):
        ctx = make_ctx(make_flutter_app(
            self.base, "app_a", deps=["firebase_analytics", "google_mobile_ads", "firebase_auth"],
            permissions=["ACCESS_FINE_LOCATION", "INTERNET", "com.google.android.gms.permission.AD_ID"],
            config={"privacy": {"data_types": ["App interactions"]}}), self.state)
        report = privacy.run_privacy(ctx)
        checks = {c["check"]: c for c in report["checks"]}
        self.assertEqual(checks["Permission inventory"]["status"], R.WARN)
        self.assertIn("ACCESS_FINE_LOCATION", checks["Permission inventory"]["detail"])
        self.assertEqual(checks["Declared vs inferred data collection"]["status"], R.FAIL)
        self.assertEqual(checks["Privacy policy URL"]["status"], R.FAIL)
        self.assertEqual(checks["Account deletion readiness"]["status"], R.FAIL)
        self.assertEqual(checks["Consent configuration"]["status"], R.WARN)
        self.assertEqual(checks["Data Safety declaration sign-off"]["status"], R.MANUAL)
        draft = report["data"]["data_safety_draft"]
        self.assertTrue(draft["status"].startswith("DRAFT"))
        location = next(d for d in draft["data_types"] if d["category"] == "Location: precise")
        self.assertIn("android.permission.ACCESS_FINE_LOCATION", location["sources"])

    def test_signoff_requires_human_and_is_bound_to_draft(self):
        root = make_flutter_app(self.base, "app_a", deps=["firebase_analytics"],
                                config={"privacy": {"data_types": ["App interactions", "Device or other IDs"],
                                                    "policy_url": "https://example.com/privacy",
                                                    "retention_policy": "90 days"}})
        ctx = make_ctx(root, self.state)
        report = privacy.run_privacy(ctx)
        item = privacy.request_signoff(ctx, report)
        A.ApprovalStore.for_app(ctx).decide(item["id"], "Asha", True)
        signed = {c["check"]: c["status"] for c in privacy.run_privacy(ctx)["checks"]}
        self.assertEqual(signed["Data Safety declaration sign-off"], R.PASS)
        (root / "pubspec.lock").write_text(
            (root / "pubspec.lock").read_text() +
            '  geolocator:\n    dependency: "direct main"\n    source: hosted\n    version: "1.0.0"\n')
        changed = {c["check"]: c["status"] for c in privacy.run_privacy(ctx)["checks"]}
        self.assertEqual(changed["Data Safety declaration sign-off"], R.MANUAL)

    def test_policy_url_reachability_uses_execute(self):
        ctx = make_ctx(make_flutter_app(self.base, "app_a", deps=["firebase_analytics"], config={
            "privacy": {"policy_url": "https://example.com/p"}}), self.state)
        self.assertEqual(next(c for c in privacy.run_privacy(ctx)["checks"]
                              if c["check"] == "Privacy policy URL")["status"], R.NOT_RUN)
        with mock.patch.object(privacy, "check_url", return_value=False):
            report = privacy.run_privacy(ctx, execute=True)
        self.assertEqual(next(c for c in report["checks"] if c["check"] == "Privacy policy URL")["status"], R.FAIL)

    def test_removed_permissions_do_not_count(self):
        root = make_flutter_app(self.base, "app_a")
        manifest = root / "android/app/src/main/AndroidManifest.xml"
        manifest.write_text(manifest.read_text().replace(
            "<application", '<uses-permission android:name="android.permission.CAMERA" tools:node="remove"/>\n    <application'))
        report = privacy.run_privacy(make_ctx(root, self.state))
        self.assertEqual(report["data"]["inferred_categories"], [])


class CliTests(Tmp):
    def _cli(self, *argv, stdin=None):
        out = io.StringIO()
        with redirect_stdout(out), mock.patch("sys.stdin", stdin or io.StringIO("")):
            code = cli_main(list(argv))
        return code, out.getvalue()

    def test_cli_secret_set_validate_and_approval_flow(self):
        root = make_flutter_app(self.base, "app_a", package="com.cli.app",
                                config={"secrets": [{"name": "API_TOKEN"}]})
        common = ["--project", str(root), "--state-root", str(self.state), "--registry", str(self.base / "none.csv")]
        code, out = self._cli("secrets", "set", "--name", "API_TOKEN", *common, stdin=io.StringIO("cli-secret-9\n"))
        self.assertEqual(code, 0)
        self.assertNotIn("cli-secret-9", out)
        code, out = self._cli("secrets", "validate", *common)
        self.assertEqual(code, 0)
        self.assertIn("[PASS]", out)
        reports = list((self.state / "apps" / "com.cli.app" / "reports" / "secrets-validate").glob("*.json"))
        self.assertEqual(len(reports), 1)
        code, _ = self._cli("privacy", "signoff", *common)
        self.assertEqual(code, 0)
        pending = A.ApprovalStore(self.state / "apps" / "com.cli.app", "com.cli.app").list("PENDING")
        self.assertEqual(len(pending), 1)
        code, out = self._cli("approvals", "approve", pending[0]["id"], "--by", "Asha", *common)
        self.assertEqual(code, 0)
        self.assertIn("APPROVED", out)
        code, out = self._cli("audit", "verify", *common)
        self.assertEqual((code, out.strip()), (0, "Audit log intact"))

    def test_cli_rejects_missing_app_selection(self):
        with mock.patch("sys.stderr", io.StringIO()) as err:
            code = cli_main(["auth", "--state-root", str(self.state)])
        self.assertEqual(code, 2)
        self.assertIn("Select an app", err.getvalue())

    def test_factory_entrypoint_runs(self):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "factory.py"), "--help"],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0)
        for name in ("secrets", "auth", "data", "privacy", "approvals", "audit"):
            self.assertIn(name, proc.stdout)


if __name__ == "__main__":
    unittest.main()
