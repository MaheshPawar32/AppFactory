"""CLI group: AI provider configuration, consent, status, usage and a minimal smoke call."""
from __future__ import annotations

import json

from .ai.providers import AIRequest, ProviderError
from .ai.service import AIService, load_config, save_config, set_consent
from .cli import group


@group("ai", "AI provider: status, configure, consent, usage, smoke")
def _ai(sub):
    sub.add_argument("action", choices=("status", "configure", "consent", "usage", "smoke"))
    sub.add_argument("--provider", choices=("none", "anthropic", "claude-code", "mock"))
    sub.add_argument("--model")
    sub.add_argument("--monthly-budget-usd", type=float)
    sub.add_argument("--grant", action="store_true")
    sub.add_argument("--revoke", action="store_true")
    sub.add_argument("--by")

    def handler(args, app):
        if args.action == "configure":
            changes = {k: v for k, v in (("provider", args.provider), ("model", args.model),
                                         ("monthly_budget_usd", args.monthly_budget_usd)) if v is not None}
            print(json.dumps(save_config(args.state_root, **changes), indent=2))
            return 0
        if args.action == "consent":
            if args.grant == args.revoke:
                raise SystemExit("Pass exactly one of --grant / --revoke")
            record = set_consent(app, args.grant, args.by)
            print(f"External AI {'allowed' if record['granted'] else 'blocked'} for {app.app_id} by {record['by']}")
            return 0
        service = AIService(app, config=load_config(args.state_root))
        if args.action == "status":
            print(json.dumps(service.status(), indent=2))
            return 0
        if args.action == "usage":
            print(json.dumps(service.usage(), indent=2))
            return 0
        # smoke: no project context is sent, only a fixed instruction.
        try:
            response = service.complete(AIRequest(
                task="smoke", prompt="Reply with JSON {\"ok\": true}.", max_tokens=200, effort="low",
                schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
                workdir=app.state_dir if app.state_dir.mkdir(parents=True, exist_ok=True) is None else None,
                max_budget_usd=0.25))
        except ProviderError as exc:
            print(f"AI smoke NOT RUN / FAILED: {exc}")
            return 1
        print(json.dumps({"result": response.data, **response.to_dict()}, indent=2))
        return 0 if response.data == {"ok": True} else 1
    return handler
