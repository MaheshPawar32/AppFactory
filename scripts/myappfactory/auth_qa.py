"""Milestone 42 — Authentication and authorization QA.

Static inspection works for every app. Live adapter checks (Firebase Auth REST,
Supabase GoTrue) run only with --execute and test credentials resolved through
the secret store; otherwise they are NOT RUN. Offline-only apps without auth are
reported NOT APPLICABLE rather than failed.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from . import reports as R
from .context import AppContext
from .project import all_dependency_names, dart_sources, line_of, load_app_config, read_text
from .runner import run
from .secrets_manager import lookup

AUTH_PACKAGES = {
    "firebase_auth": "firebase", "supabase_flutter": "supabase", "supabase": "supabase",
    "google_sign_in": "google", "sign_in_with_apple": "apple", "flutter_appauth": "oauth",
    "amplify_auth_cognito": "cognito", "local_auth": "biometric",
}
SECURE_STORAGE = {"flutter_secure_storage"}
SCENARIOS = {
    "login": r"login|sign_?in",
    "logout": r"logout|sign_?out",
    "session_expiry": r"session|expir|refresh",
    "roles": r"role|permission|authori[sz]",
    "unauthorized": r"unauthori[sz]ed|forbidden|denied|guard",
    "auth_errors": r"auth.*error|invalid_credential|wrong_password",
}
FIREBASE_SIGNIN = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={key}"


def detect(app: AppContext) -> dict:
    deps = all_dependency_names(app.root)
    config = load_app_config(app.root)
    auth_cfg = (config.get("integrations") or {}).get("authentication") or {}
    providers = sorted({AUTH_PACKAGES[d] for d in deps if d in AUTH_PACKAGES})
    return {"declared_enabled": bool(auth_cfg.get("enabled")), "declared_provider": auth_cfg.get("provider", "none"),
            "packages": sorted(d for d in deps if d in AUTH_PACKAGES), "providers": providers,
            "secure_storage": bool(deps & SECURE_STORAGE),
            "applicable": bool(auth_cfg.get("enabled")) or bool(providers)}


def static_token_checks(app: AppContext) -> list[dict]:
    issues = []
    rules = [
        ("token_in_shared_preferences", re.compile(
            r"(?i)(prefs|sharedPreferences|SharedPreferences)[\w.]*\.setString\(\s*['\"][^'\"]*(token|session|jwt)"),
         "Auth token written to SharedPreferences (plain-text); use flutter_secure_storage"),
        ("token_logged", re.compile(r"(?i)(print|debugPrint|log)\([^)]*(access_?token|id_?token|refresh_?token|jwt)"),
         "Token value may be written to logs"),
        ("hardcoded_bearer", re.compile(r"(?i)['\"]Bearer\s+[A-Za-z0-9._-]{16,}['\"]"),
         "Hard-coded bearer token"),
        ("insecure_http", re.compile(r"['\"]http://(?!localhost|127\.0\.0\.1|10\.0\.2\.2)[^'\"]+['\"]"),
         "Plain HTTP endpoint; credentials may be sent unencrypted"),
        ("supabase_service_role", re.compile(r"(?i)service_?role"),
         "Supabase service-role key referenced in client code; it bypasses row-level security"),
    ]
    for path in dart_sources(app.root):
        if "/test/" in str(path) or path.parts[-2] == "test":
            continue
        text = read_text(path) or ""
        for rule_id, pattern, message in rules:
            for match in pattern.finditer(text):
                issues.append({"rule": rule_id, "file": str(path.relative_to(app.root)),
                               "line": line_of(text, match.start()), "message": message})
    return issues


def discover_auth_tests(app: AppContext) -> dict:
    found = {name: [] for name in SCENARIOS}
    for path in dart_sources(app.root):
        if not path.name.endswith("_test.dart"):
            continue
        relative = str(path.relative_to(app.root))
        text = (read_text(path) or "").lower()
        names = " ".join(re.findall(r"(?:test|testWidgets|group)\(\s*['\"]([^'\"]+)", text)) + " " + path.name
        for scenario, pattern in SCENARIOS.items():
            if re.search(pattern, names):
                found[scenario].append(relative)
    return found


def firebase_live_check(api_key, email, password, opener=urllib.request.urlopen, timeout=15) -> dict:
    """Sign in a dedicated test account and verify a bad password is rejected."""
    def call(pw):
        body = json.dumps({"email": email, "password": pw, "returnSecureToken": True}).encode()
        request = urllib.request.Request(FIREBASE_SIGNIN.format(key=api_key), data=body,
                                         headers={"Content-Type": "application/json"})
        try:
            with opener(request, timeout=timeout) as response:
                return response.status, json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as exc:
            return exc.code, {}
    ok_status, ok_body = call(password)
    bad_status, _ = call(password + "-invalid")
    return {"login": ok_status == 200 and bool(ok_body.get("idToken")),
            "token_expiry_seconds": int(ok_body.get("expiresIn", 0) or 0),
            "rejects_bad_password": bad_status in (400, 401, 403)}


def supabase_live_check(url, anon_key, email, password, opener=urllib.request.urlopen, timeout=15) -> dict:
    def call(pw):
        body = json.dumps({"email": email, "password": pw}).encode()
        request = urllib.request.Request(url.rstrip("/") + "/auth/v1/token?grant_type=password", data=body,
                                         headers={"Content-Type": "application/json", "apikey": anon_key})
        try:
            with opener(request, timeout=timeout) as response:
                return response.status, json.loads(response.read() or b"{}")
        except urllib.error.HTTPError as exc:
            return exc.code, {}
    ok_status, ok_body = call(password)
    bad_status, _ = call(password + "-invalid")
    unauth_status = None
    request = urllib.request.Request(url.rstrip("/") + "/auth/v1/user", headers={"apikey": anon_key})
    try:
        with opener(request, timeout=timeout) as response:
            unauth_status = response.status
    except urllib.error.HTTPError as exc:
        unauth_status = exc.code
    return {"login": ok_status == 200 and bool(ok_body.get("access_token")),
            "token_expiry_seconds": int(ok_body.get("expires_in", 0) or 0),
            "rejects_bad_password": bad_status in (400, 401, 403),
            "rejects_unauthenticated_user_endpoint": unauth_status in (401, 403)}


def _live_checks(app, info, environment, opener):
    results, checks = {}, []
    if "firebase" in info["providers"]:
        values = {n: lookup(app, environment, n)[0] for n in ("FIREBASE_WEB_API_KEY", "AUTH_TEST_EMAIL", "AUTH_TEST_PASSWORD")}
        if all(values.values()):
            try:
                results["firebase"] = firebase_live_check(values["FIREBASE_WEB_API_KEY"], values["AUTH_TEST_EMAIL"],
                                                          values["AUTH_TEST_PASSWORD"], opener)
                good = results["firebase"]["login"] and results["firebase"]["rejects_bad_password"]
                checks.append(R.check("Firebase live login / bad-password rejection", R.PASS if good else R.FAIL,
                                      json.dumps(results["firebase"])))
            except (urllib.error.URLError, OSError, ValueError) as exc:
                checks.append(R.check("Firebase live check", R.FAIL, f"Request failed: {exc.__class__.__name__}"))
        else:
            checks.append(R.check("Firebase live check", R.NOT_RUN,
                                  "Needs FIREBASE_WEB_API_KEY, AUTH_TEST_EMAIL, AUTH_TEST_PASSWORD in the secret store"))
    if "supabase" in info["providers"]:
        values = {n: lookup(app, environment, n)[0] for n in ("SUPABASE_URL", "SUPABASE_ANON_KEY", "AUTH_TEST_EMAIL", "AUTH_TEST_PASSWORD")}
        if all(values.values()):
            try:
                results["supabase"] = supabase_live_check(values["SUPABASE_URL"], values["SUPABASE_ANON_KEY"],
                                                          values["AUTH_TEST_EMAIL"], values["AUTH_TEST_PASSWORD"], opener)
                good = all(results["supabase"][k] for k in ("login", "rejects_bad_password",
                                                            "rejects_unauthenticated_user_endpoint"))
                checks.append(R.check("Supabase live login / rejection checks", R.PASS if good else R.FAIL,
                                      json.dumps(results["supabase"])))
            except (urllib.error.URLError, OSError, ValueError) as exc:
                checks.append(R.check("Supabase live check", R.FAIL, f"Request failed: {exc.__class__.__name__}"))
        else:
            checks.append(R.check("Supabase live check", R.NOT_RUN,
                                  "Needs SUPABASE_URL, SUPABASE_ANON_KEY, AUTH_TEST_EMAIL, AUTH_TEST_PASSWORD in the secret store"))
    return checks, results


def run_auth_qa(app: AppContext, execute=False, environment="development", opener=urllib.request.urlopen) -> dict:
    info = detect(app)
    if not info["applicable"]:
        return R.make_report(app, "auth-qa", "Authentication & authorization QA",
                             [R.check("Authentication", R.NOT_APPLICABLE,
                                      "No auth packages and APP_CONFIG authentication.enabled is false")],
                             milestone=42, data=info, status=R.PASS)
    checks = []
    if info["declared_enabled"] and not info["providers"]:
        checks.append(R.check("Declared vs implemented", R.FAIL, "APP_CONFIG enables auth but no auth package is present"))
    elif info["providers"] and not info["declared_enabled"]:
        checks.append(R.check("Declared vs implemented", R.WARN, "Auth packages present but APP_CONFIG does not declare auth"))
    else:
        checks.append(R.check("Declared vs implemented", R.PASS, f"Providers: {', '.join(info['providers'])}"))
    checks.append(R.check("Secure token storage", R.PASS if info["secure_storage"] else R.WARN,
                          "flutter_secure_storage present" if info["secure_storage"]
                          else "No secure storage package; confirm the SDK persists sessions securely"))
    issues = static_token_checks(app)
    checks.append(R.check("Token handling (static)", R.FAIL if issues else R.PASS,
                          f"{len(issues)} issue(s)" if issues else "No risky token patterns found"))
    tests = discover_auth_tests(app)
    for scenario, files in tests.items():
        checks.append(R.check(f"Test coverage: {scenario}", R.PASS if files else R.NOT_RUN,
                              ", ".join(files) if files else "No test found — add one"))
    commands = []
    test_files = sorted({f for files in tests.values() for f in files})
    if execute and test_files:
        result = run(["flutter", "test", *test_files], app.root, timeout=900)
        commands.append(result.to_dict())
        checks.append(R.check("Auth test execution", result.status, f"exit {result.returncode}"))
    elif test_files:
        checks.append(R.check("Auth test execution", R.NOT_RUN, "Pass --execute to run discovered auth tests"))
    live = {}
    if execute:
        live_checks, live = _live_checks(app, info, environment, opener)
        checks += live_checks
    else:
        checks.append(R.check("Live provider checks", R.NOT_RUN, "Pass --execute with test credentials configured"))
    return R.make_report(app, "auth-qa", "Authentication & authorization QA", checks, milestone=42,
                         data={**info, "token_issues": issues, "tests": tests, "live": live},
                         commands=commands,
                         limitations=["Static checks are heuristics.",
                                      "Role/permission enforcement must also be verified server-side (rules/RLS)."],
                         manual=["Log in, background the app past session expiry, and confirm re-authentication.",
                                 "Confirm logout clears secure storage and cached user data.",
                                 "Confirm server rules reject another user's records."])
