"""Milestones 45 and 49 — testing engine and dependency/vulnerability/license audit.

Builds on scripts/quality_qa_engine.py (discovery, static inventory, SBOM) and adds:
per-test JSON-reporter parsing, failure classification, coverage, per-app test
history with new/fixed failure trends, Python test execution, outdated-package
reports, OSV.dev vulnerability queries and license-compatibility classification.
"""
from __future__ import annotations

import json
import re
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import reports as R
from .context import AppContext
from .project import lock_packages
from .runner import ALLOWED_EXECUTABLES, run

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import quality_qa_engine as QE  # noqa: E402

FAILURE_CLASSES = (
    ("compile_error", re.compile(r"\.dart:\d+:\d+: Error|Compilation failed|Error: The (method|getter|setter)")),
    ("layout_overflow", re.compile(r"RenderFlex overflowed|overflowed by")),
    ("missing_plugin", re.compile(r"MissingPluginException")),
    ("timeout", re.compile(r"TimeoutException|Test timed out|timed out after")),
    ("pending_timer", re.compile(r"A Timer is still pending")),
    ("null_error", re.compile(r"Null check operator|Unexpected null value|NoSuchMethodError")),
    ("network", re.compile(r"SocketException|HttpException|ClientException")),
    ("golden_mismatch", re.compile(r"[Gg]olden.*(mismatch|differ)|Pixel test failed")),
    ("assertion", re.compile(r"Expected:|TestFailure|expect\(")),
    ("python_assertion", re.compile(r"AssertionError")),
)


def classify_failure(text: str) -> str:
    for name, pattern in FAILURE_CLASSES:
        if pattern.search(text or ""):
            return name
    return "exception"


def parse_flutter_json(stdout: str) -> dict:
    """Parse `flutter test --reporter json` output into counts and failures."""
    tests, errors, prints = {}, {}, []
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = event.get("type")
        if kind == "testStart":
            test = event.get("test", {})
            tests[test.get("id")] = {"name": test.get("name", ""), "result": None, "skipped": False, "hidden": False}
        elif kind == "testDone" and event.get("testID") in tests:
            tests[event["testID"]].update(result=event.get("result"), skipped=event.get("skipped", False),
                                          hidden=event.get("hidden", False))
        elif kind == "error":
            errors.setdefault(event.get("testID"), []).append(str(event.get("error", "")))
        elif kind == "print":
            prints.append(event.get("message", ""))
    visible = {k: v for k, v in tests.items() if not v["hidden"] and v["result"] is not None}
    failures = []
    for test_id, test in visible.items():
        if test["result"] in ("failure", "error"):
            message = "\n".join(errors.get(test_id, []))
            failures.append({"test": test["name"], "class": classify_failure(message),
                             "message": message.strip().splitlines()[0][:300] if message.strip() else ""})
    return {"total": len(visible), "passed": sum(t["result"] == "success" and not t["skipped"] for t in visible.values()),
            "failed": len(failures), "skipped": sum(t["skipped"] for t in visible.values()),
            "failures": failures, "prints": prints}


def parse_lcov(path: Path) -> dict | None:
    if not path.is_file():
        return None
    found = hit = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("LF:"):
            found += int(line[3:])
        elif line.startswith("LH:"):
            hit += int(line[3:])
    return {"lines_found": found, "lines_hit": hit, "percent": round(100 * hit / found, 1) if found else 0.0}


def _history_path(app):
    return app.state_path("qa", "test_history.jsonl")


def test_history(app) -> list[dict]:
    path = _history_path(app)
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.is_file() else []


def trend(previous: dict | None, current: dict) -> dict:
    if not previous:
        return {"baseline": True}
    before = {f["test"] for f in previous.get("failures", [])}
    now = {f["test"] for f in current.get("failures", [])}
    delta_cov = None
    if previous.get("coverage") and current.get("coverage"):
        delta_cov = round(current["coverage"]["percent"] - previous["coverage"]["percent"], 1)
    return {"baseline": False, "new_failures": sorted(now - before), "fixed": sorted(before - now),
            "still_failing": sorted(now & before), "coverage_delta": delta_cov,
            "total_delta": current["total"] - previous.get("total", 0)}


def _python_tests(root: Path) -> list[str]:
    tests_dir = root / "tests"
    return sorted(str(p.relative_to(root)) for p in tests_dir.glob("test_*.py")) if tests_dir.is_dir() else []


def run_tests(app: AppContext, execute=False, coverage=False, device=None,
              cancel_event: threading.Event | None = None, timeout=1200) -> dict:
    plan = QE.discover_test_plan(app.root, device)
    python_files = _python_tests(app.root)
    checks, suites, commands = [], [], []
    totals = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "failures": []}
    for suite in plan:
        entry = {"suite": suite["suite"], "files": suite.get("files", []), "status": R.NOT_RUN,
                 "reason": suite.get("reason", "")}
        if suite["status"] != "PLANNED":
            entry["reason"] = entry["reason"] or "No test files in this category"
        elif not execute:
            entry["reason"] = "Planned; pass --execute"
        else:
            command = list(suite["command"])
            if command[:2] == ["flutter", "test"]:
                command = command[:2] + ["--reporter", "json"] + (["--coverage"] if coverage else []) + command[2:]
            result = run(command, app.root, timeout=timeout, cancel_event=cancel_event)
            commands.append(result.to_dict(tail_lines=10))
            if result.cancelled:
                entry.update(status=R.NOT_RUN, reason="Cancelled")
            elif result.not_found:
                entry.update(status=R.BLOCKED, reason="flutter not found")
            else:
                parsed = parse_flutter_json(result.stdout)
                if parsed["total"] == 0 and not result.ok:
                    parsed["failures"] = [{"test": f"<{suite['suite']} suite>", "class": classify_failure(result.stdout + result.stderr),
                                           "message": (result.stderr or result.stdout).strip().splitlines()[-1:][0][:300]
                                           if (result.stderr or result.stdout).strip() else "no output"}]
                    parsed["failed"] = 1
                entry.update(status=R.PASS if result.ok and parsed["failed"] == 0 else R.FAIL,
                             **{k: parsed[k] for k in ("total", "passed", "failed", "skipped", "failures")})
                for key in ("total", "passed", "failed", "skipped"):
                    totals[key] += parsed[key]
                totals["failures"] += parsed["failures"]
        suites.append(entry)
        checks.append(R.check(f"Suite: {suite['suite']}", entry["status"],
                              entry.get("reason") or f"{entry.get('passed', 0)}/{entry.get('total', 0)} passed"))
    if python_files:
        if execute:
            result = run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], app.root, timeout=timeout,
                         cancel_event=cancel_event, allowed=ALLOWED_EXECUTABLES | {Path(sys.executable).name})
            commands.append(result.to_dict(tail_lines=10))
            match = re.search(r"Ran (\d+) tests?", result.stderr)
            ran = int(match.group(1)) if match else 0
            failed = sum(int(n) for n in re.findall(r"(?:failures|errors)=(\d+)", result.stderr))
            totals["total"] += ran
            totals["passed"] += max(ran - failed, 0)
            totals["failed"] += failed
            if failed:
                totals["failures"].append({"test": "<python unittest>", "class": "python_assertion",
                                           "message": result.stderr.strip().splitlines()[-1][:300]})
            checks.append(R.check("Suite: python", R.PASS if result.ok else R.FAIL, f"{ran} test(s), {failed} failed"))
        else:
            checks.append(R.check("Suite: python", R.NOT_RUN, f"{len(python_files)} file(s); pass --execute"))
    cov = parse_lcov(app.root / "coverage" / "lcov.info") if (execute and coverage) else None
    if coverage:
        checks.append(R.check("Coverage", R.PASS if cov else R.NOT_RUN,
                              f"{cov['percent']}% of {cov['lines_found']} lines" if cov else "No lcov.info produced"))
    current = {"at": datetime.now(timezone.utc).isoformat(), **{k: totals[k] for k in ("total", "passed", "failed", "skipped")},
               "failures": totals["failures"], "coverage": cov,
               "suites": {s["suite"]: s["status"] for s in suites}}
    history = test_history(app)
    trend_info = trend(history[-1] if history else None, current) if execute else {}
    if execute and totals["total"]:
        path = _history_path(app)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(current) + "\n")
    if trend_info.get("new_failures"):
        checks.append(R.check("Regression vs previous run", R.FAIL, "New failures: " + ", ".join(trend_info["new_failures"][:10])))
    by_class = {}
    for failure in totals["failures"]:
        by_class[failure["class"]] = by_class.get(failure["class"], 0) + 1
    return R.make_report(app, "tests", "Automated testing engine", checks, milestone=45,
                         data={"suites": suites, "totals": {k: totals[k] for k in ("total", "passed", "failed", "skipped")},
                               "failures": totals["failures"], "failure_classes": by_class,
                               "coverage": cov, "trend": trend_info, "history_runs": len(history) + (1 if execute and totals["total"] else 0)},
                         commands=commands,
                         limitations=["Categories are assigned by file path/name conventions.",
                                      "Integration tests need a selected device (--device)."])


# --- Milestone 49 -----------------------------------------------------------

PERMISSIVE = re.compile(r"\b(MIT|BSD|Apache|ISC|Zlib|Unlicense|CC0|Boost|PSF|Python Software)\b", re.I)
WEAK_COPYLEFT = re.compile(r"\b(LGPL|MPL|Mozilla Public|EPL|Eclipse Public|CDDL)\b", re.I)
STRONG_COPYLEFT = re.compile(r"\b(AGPL|GPL|General Public License|SSPL|EUPL)\b", re.I)
OSV_BATCH = "https://api.osv.dev/v1/querybatch"
OSV_VULN = "https://api.osv.dev/v1/vulns/{id}"


def classify_license(text: str | None) -> str:
    text = text or ""
    if STRONG_COPYLEFT.search(text) and not re.search(r"\bLGPL|Lesser General", text, re.I):
        return "strong_copyleft"
    if WEAK_COPYLEFT.search(text) or re.search(r"Lesser General", text, re.I):
        return "weak_copyleft"
    if PERMISSIVE.search(text):
        return "permissive"
    return "unknown"


def parse_pub_outdated(stdout: str) -> list[dict]:
    try:
        data = json.loads(stdout[stdout.index("{"):])
    except (ValueError, json.JSONDecodeError):
        return []
    rows = []
    for package in data.get("packages", []):
        def version(key):
            item = package.get(key) or {}
            return item.get("version") if isinstance(item, dict) else None
        current, latest, resolvable = version("current"), version("latest"), version("resolvable")
        if current and latest and current != latest:
            major_behind = current.split(".")[0] != latest.split(".")[0] or (
                current.startswith("0.") and current.split(".")[1] != latest.split(".")[1])
            rows.append({"package": package.get("package"), "current": current, "resolvable": resolvable,
                         "latest": latest, "kind": package.get("kind"), "major_behind": major_behind})
    return rows


def osv_query(packages: dict, opener=urllib.request.urlopen, timeout=30) -> dict:
    """Query OSV.dev for Pub packages. Sends only package names and versions."""
    names = [n for n, info in sorted(packages.items()) if info.get("version") and info.get("source", "hosted") == "hosted"]
    body = json.dumps({"queries": [{"package": {"name": n, "ecosystem": "Pub"}, "version": packages[n]["version"]}
                                   for n in names]}).encode()
    request = urllib.request.Request(OSV_BATCH, data=body, headers={"Content-Type": "application/json"})
    with opener(request, timeout=timeout) as response:
        results = json.loads(response.read()).get("results", [])
    findings = []
    for name, result in zip(names, results):
        for vuln in result.get("vulns", []) or []:
            detail = {}
            try:
                with opener(urllib.request.Request(OSV_VULN.format(id=vuln["id"])), timeout=timeout) as response:
                    detail = json.loads(response.read())
            except (urllib.error.URLError, OSError, ValueError):
                pass
            severity = (detail.get("database_specific") or {}).get("severity") or \
                ("SEE ADVISORY" if detail.get("severity") else "UNKNOWN")
            findings.append({"package": name, "version": packages[name]["version"], "id": vuln["id"],
                             "summary": detail.get("summary", ""), "severity": severity,
                             "aliases": detail.get("aliases", [])})
    return {"queried": len(names), "findings": findings}


def run_dependency_audit(app: AppContext, execute=False, osv=False, gradle=False, opener=urllib.request.urlopen) -> dict:
    output_dir = app.state_path("qa", "dependencies", datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    output_dir.mkdir(parents=True, exist_ok=True)
    base = QE.run_dependency_audit(app.root, execute, output_dir, False, gradle)
    packages = lock_packages(app.root)
    direct = sorted(n for n, p in packages.items() if p.get("dependency", "").startswith("direct"))
    checks = [R.check("Direct dependencies", R.PASS if packages else R.NOT_RUN, f"{len(direct)} direct, "
                      f"{len(packages) - len(direct)} transitive (pubspec.lock)" if packages else "No pubspec.lock")]
    pub_deps = base.get("flutter_pub_deps", {})
    checks.append(R.check("Resolved graph (flutter pub deps)", pub_deps.get("status", R.NOT_RUN)
                          if pub_deps.get("status") in R.CHECK_STATUSES else R.NOT_RUN, pub_deps.get("reason", "")))
    gradle_result = base.get("android_gradle_dependencies", {})
    checks.append(R.check("Gradle dependency inventory", gradle_result.get("status", R.NOT_RUN)
                          if gradle_result.get("status") in R.CHECK_STATUSES else R.NOT_RUN, gradle_result.get("reason", "")))
    commands, outdated = [], []
    if execute:
        result = run(["flutter", "pub", "outdated", "--json"], app.root, timeout=300)
        commands.append(result.to_dict(tail_lines=5))
        outdated = parse_pub_outdated(result.stdout) if result.ok else []
        majors = [o["package"] for o in outdated if o["major_behind"]]
        checks.append(R.check("Outdated packages", (R.WARN if majors else R.PASS) if result.ok else R.FAIL,
                              f"{len(outdated)} behind latest; major versions behind: {', '.join(majors) or 'none'}"))
    else:
        checks.append(R.check("Outdated packages", R.NOT_RUN, "Pass --execute (runs flutter pub outdated)"))
    vulns = None
    if execute and osv and packages:
        try:
            vulns = osv_query(packages, opener)
            checks.append(R.check("Known vulnerabilities (OSV.dev)", R.FAIL if vulns["findings"] else R.PASS,
                                  f"{len(vulns['findings'])} advisory(ies) across {vulns['queried']} hosted packages"))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            checks.append(R.check("Known vulnerabilities (OSV.dev)", R.NOT_RUN, f"OSV query failed: {exc.__class__.__name__}"))
    else:
        checks.append(R.check("Known vulnerabilities (OSV.dev)", R.NOT_RUN,
                              "Pass --execute --osv; static inventory is not a vulnerability scan"))
    licenses = []
    for item in base.get("licenses", []):
        licenses.append({"package": item.get("name"), "version": item.get("version"),
                         "license_class": classify_license(item.get("declared_license") or
                                                           " ".join(item.get("license_files", []))),
                         "declared": (item.get("declared_license") or "")[:80]})
    strong = [l["package"] for l in licenses if l["license_class"] == "strong_copyleft"]
    unknown = [l["package"] for l in licenses if l["license_class"] == "unknown"]
    if licenses:
        checks.append(R.check("License compatibility", R.WARN if strong or unknown else R.PASS,
                              f"strong copyleft: {', '.join(strong) or 'none'}; unknown: {len(unknown)}"))
    else:
        checks.append(R.check("License compatibility", R.NOT_RUN, "No license metadata found in the local pub cache"))
    bom = None
    if base.get("sbom", {}).get("status") == "PASS":
        bom = QE._cyclonedx(app.root, base.get("flutter_dependencies", []))
        (output_dir / "bom.cdx.json").write_text(json.dumps(bom, indent=2), encoding="utf-8")
    checks.append(R.check("SBOM (CycloneDX 1.5)", R.PASS if bom else R.NOT_RUN,
                          str(output_dir / "bom.cdx.json") if bom else "No package inventory"))
    return R.make_report(app, "dependencies", "Dependency, vulnerability & license audit", checks, milestone=49,
                         data={"direct": direct, "transitive_count": len(packages) - len(direct), "outdated": outdated,
                               "vulnerabilities": vulns, "licenses": licenses, "output_dir": str(output_dir)},
                         commands=commands,
                         limitations=["License classification is a heuristic, not legal review.",
                                      "OSV.dev coverage of Pub advisories is incomplete; no result ≠ no vulnerability.",
                                      "Gradle (Android) dependencies are inventoried only with --gradle."])
