"""AI provider architecture: kinds, consent, context filtering, retries, validation, usage."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from factory_fixtures import make_ctx, make_flutter_app

from myappfactory import context
from myappfactory.ai import providers as P
from myappfactory.ai import schema as S
from myappfactory.ai import service as SV
from myappfactory.runner import CommandResult

FAKE_KEY = "sk-ant-" + "q" * 30


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.state = self.base / "state"
        self.root = make_flutter_app(self.base, "app_a", files={
            "lib/home.dart": f"const k = '{FAKE_KEY}';\nclass Home {{}}\n", ".env": "SECRET=1",
            "android/app/upload.jks": "x"})
        self.app = make_ctx(self.root, self.state)

    def tearDown(self):
        self._tmp.cleanup()

    def service(self, provider, **config):
        return SV.AIService(self.app, provider, {**SV.DEFAULT_CONFIG, "min_interval_seconds": 0, **config},
                            sleep=lambda s: None)


class SchemaTests(unittest.TestCase):
    def test_validate_and_strict(self):
        schema = S.strict({"type": "object", "properties": {"a": {"type": "integer"},
                                                            "b": {"type": "array", "items": {"type": "string"}}}})
        self.assertEqual(schema["required"], ["a", "b"])
        self.assertEqual(S.validate({"a": 1, "b": ["x"]}, schema), [])
        self.assertTrue(S.validate({"a": True, "b": []}, schema))  # bool is not integer
        self.assertTrue(S.validate({"a": 1, "b": [], "c": 2}, schema))
        self.assertTrue(S.validate({"b": []}, schema))


class ServiceTests(Base):
    def test_none_provider_reports_needs_configuration_and_local_fallback(self):
        svc = self.service(P.NoneProvider())
        self.assertEqual(svc.status()["status"], "NEEDS MANUAL CONFIGURATION")
        result = SV.run_ai_or_local(self.app, P.AIRequest("t", "p"), lambda: {"local": 1}, svc)
        self.assertEqual((result["source"], result["data"]), ("local", {"local": 1}))
        self.assertIn("ai_unavailable_reason", result)

    def test_mock_output_is_always_labelled_mock(self):
        svc = self.service(P.MockProvider([{"ok": True}]))
        result = SV.run_ai_or_local(self.app, P.AIRequest("t", "p", schema={"type": "object",
                                    "properties": {"ok": {"type": "boolean"}}}), lambda: None, svc)
        self.assertEqual(result["source"], "mock")
        self.assertEqual(result["data"], {"ok": True})
        self.assertEqual(svc.usage()[0]["kind"], "mock")

    def test_external_requires_named_human_consent(self):
        provider = P.MockProvider([{"ok": True}])
        provider.kind = P.EXTERNAL  # simulate an external provider
        svc = self.service(provider)
        self.assertEqual(svc.status()["status"], "CONFIGURED — app consent missing")
        with self.assertRaises(P.ProviderNotConfigured):
            svc.complete(P.AIRequest("t", "p"))
        self.assertEqual(provider.requests, [])  # nothing left the machine
        with self.assertRaises(PermissionError):
            SV.set_consent(self.app, True, "agent")
        SV.set_consent(self.app, True, "Asha")
        self.assertEqual(svc.status()["status"], "CONNECTED")
        svc.complete(P.AIRequest("t", "p"))

    def test_consent_is_per_app(self):
        other = make_ctx(make_flutter_app(self.base, "app_b"), self.state)
        SV.set_consent(self.app, True, "Asha")
        self.assertIsNone(SV.consent(other))

    def test_retries_retryable_errors_and_validates_structured_output(self):
        provider = P.MockProvider([P.ProviderError("429", retryable=True), "not json", {"ok": True}])
        svc = self.service(provider, max_retries=2)
        response = svc.complete(P.AIRequest("t", "p", schema={"type": "object",
                                                               "properties": {"ok": {"type": "boolean"}}}))
        self.assertEqual(response.data, {"ok": True})
        errors = [u["error"] for u in svc.usage()]
        self.assertEqual(len(errors), 3)
        self.assertIsNone(errors[-1])

    def test_non_retryable_error_stops_and_falls_back_locally(self):
        provider = P.MockProvider([P.ProviderError("400 bad"), {"never": 1}])
        result = SV.run_ai_or_local(self.app, P.AIRequest("t", "p"), lambda: "local", self.service(provider))
        self.assertEqual(result["source"], "local")
        self.assertIn("400", result["ai_error"])
        self.assertEqual(len(provider.requests), 1)

    def test_monthly_budget_blocks_external_calls(self):
        provider = P.MockProvider([{"ok": 1}])
        provider.kind = P.EXTERNAL
        SV.set_consent(self.app, True, "Asha")
        svc = self.service(provider, monthly_budget_usd=1.0)
        ledger = self.app.state_path("ai", "usage.jsonl")
        from datetime import datetime, timezone
        ledger.write_text(json.dumps({"at": datetime.now(timezone.utc).isoformat(), "kind": "external",
                                      "cost_usd": 1.5}) + "\n")
        with self.assertRaises(P.ProviderNotConfigured):
            svc.complete(P.AIRequest("t", "p"))

    def test_rate_limit_waits_between_calls(self):
        waits = []
        provider = P.MockProvider([{"a": 1}, {"a": 2}])
        svc = SV.AIService(self.app, provider, {**SV.DEFAULT_CONFIG, "min_interval_seconds": 5},
                           sleep=waits.append)
        svc.complete(P.AIRequest("t", "p"))
        svc.complete(P.AIRequest("t", "p"))
        self.assertTrue(waits and waits[-1] > 4)


class ContextTests(Base):
    def test_context_is_redacted_contained_and_excludes_secret_files(self):
        text, files = SV.collect_context(self.app)
        self.assertIn("lib/home.dart", files)
        self.assertNotIn(FAKE_KEY, text)
        self.assertNotIn(".env", files)
        self.assertFalse(any(f.endswith(".jks") for f in files))
        with self.assertRaises(context.IsolationError):
            SV.collect_context(self.app, ["../../etc/passwd"])

    def test_context_limit(self):
        text, files = SV.collect_context(self.app, max_chars=50)
        self.assertIn("context limit reached", text)


class AnthropicAdapterTests(Base):
    def _client(self, stop_reason="end_turn", text='{"ok": true}'):
        response = SimpleNamespace(
            stop_reason=stop_reason, model="claude-opus-5-5",
            content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text=text)],
            usage=SimpleNamespace(input_tokens=1000, output_tokens=500, cache_read_input_tokens=0))
        create = mock.Mock(return_value=response)
        return SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=create))), create

    def test_request_shape_usage_and_cost(self):
        client, create = self._client()
        provider = P.AnthropicProvider(client=client)
        result = provider.complete(P.AIRequest("t", "hello", system="sys", effort="medium",
                                               schema={"type": "object"}))
        params = create.call_args.kwargs
        self.assertEqual(params["model"], "claude-opus-5-5")
        self.assertEqual(params["output_config"], {"effort": "medium",
                                                   "format": {"type": "json_schema", "schema": {"type": "object"}}})
        self.assertEqual(params["fallbacks"], "default")
        self.assertNotIn("thinking", params)
        self.assertEqual(result.text, '{"ok": true}')
        self.assertEqual(result.kind, P.EXTERNAL)
        self.assertEqual(result.cost_usd, 0.014)  # 1000*4/1e6 + 500*20/1e6
        self.assertEqual(result.cost_basis, "estimated")

    def test_refusal_is_an_error(self):
        client, _ = self._client(stop_reason="refusal")
        with self.assertRaises(P.ProviderError):
            P.AnthropicProvider(client=client).complete(P.AIRequest("t", "p"))

    def test_not_configured_without_sdk(self):
        provider = P.AnthropicProvider()
        with mock.patch.object(provider, "_sdk", return_value=None):
            ok, reason = provider.available()
        self.assertFalse(ok)
        self.assertIn("anthropic", reason)


class ClaudeCodeAdapterTests(Base):
    def test_read_only_command_shape_and_parsing(self):
        calls = []

        def fake_run(cmd, cwd, timeout, allowed):
            calls.append(cmd)
            return CommandResult(cmd, str(cwd), 0, stdout=json.dumps(
                {"result": "", "structured_output": {"ok": True}, "total_cost_usd": 0.02,
                 "usage": {"input_tokens": 10, "output_tokens": 5}}))

        provider = P.ClaudeCodeProvider(run_fn=fake_run)
        result = provider.complete(P.AIRequest("t", "p", schema={"type": "object"}, workdir=self.root))
        cmd = calls[0]
        self.assertEqual(cmd[cmd.index("--allowedTools") + 1], "Read,Grep,Glob")
        self.assertIn("Bash", cmd[cmd.index("--disallowedTools") + 1])
        self.assertNotIn("--permission-mode", cmd)
        self.assertEqual(result.data, {"ok": True})
        self.assertEqual((result.cost_usd, result.cost_basis), (0.02, "reported"))

    def test_edit_mode_and_error_handling(self):
        def failing(cmd, cwd, timeout, allowed):
            return CommandResult(cmd, str(cwd), 1, stdout=json.dumps({"is_error": True, "result": "boom"}))

        with self.assertRaises(P.ProviderError):
            P.ClaudeCodeProvider(run_fn=failing).complete(P.AIRequest("t", "p", workdir=self.root, allow_edits=True))
        with self.assertRaises(P.ProviderError):
            P.ClaudeCodeProvider().complete(P.AIRequest("t", "p"))  # no workdir


if __name__ == "__main__":
    unittest.main()
