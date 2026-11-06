"""Milestone 44 — Privacy and data protection inventory.

Produces evidence for a human privacy review: permissions, third-party SDKs,
inferred vs declared data collection, policy/deletion/consent readiness and a
DRAFT Play Data Safety mapping. It never claims legal compliance; declarations
become "signed off" only through an explicit privacy_declaration approval bound
to the exact draft content.
"""
from __future__ import annotations

import urllib.error
import urllib.request

from . import reports as R
from .approvals import ApprovalStore, payload_hash
from .context import AppContext
from .project import android_manifests, lock_packages, load_app_config, manifest_permissions, read_text

# permission -> (risk, Data Safety categories it can expose)
PERMISSIONS = {
    "ACCESS_FINE_LOCATION": ("high", ["Location: precise"]),
    "ACCESS_COARSE_LOCATION": ("high", ["Location: approximate"]),
    "ACCESS_BACKGROUND_LOCATION": ("high", ["Location: precise"]),
    "CAMERA": ("high", ["Photos and videos"]),
    "RECORD_AUDIO": ("high", ["Audio"]),
    "READ_CONTACTS": ("high", ["Contacts"]),
    "WRITE_CONTACTS": ("high", ["Contacts"]),
    "READ_CALENDAR": ("high", ["Calendar events"]),
    "READ_SMS": ("high", ["Messages: SMS or MMS"]),
    "READ_CALL_LOG": ("high", ["Calls"]),
    "READ_PHONE_STATE": ("medium", ["Device or other IDs"]),
    "READ_MEDIA_IMAGES": ("medium", ["Photos and videos"]),
    "READ_MEDIA_VIDEO": ("medium", ["Photos and videos"]),
    "READ_MEDIA_AUDIO": ("medium", ["Audio"]),
    "READ_EXTERNAL_STORAGE": ("medium", ["Files and docs"]),
    "BODY_SENSORS": ("high", ["Health info"]),
    "ACTIVITY_RECOGNITION": ("medium", ["Fitness info"]),
    "POST_NOTIFICATIONS": ("low", []),
    "INTERNET": ("low", []),
    "QUERY_ALL_PACKAGES": ("high", ["Installed apps"]),
    "com.google.android.gms.permission.AD_ID": ("medium", ["Device or other IDs"]),
}

# SDK -> (purpose, Data Safety categories commonly collected). Verify against each SDK's own disclosure.
SDKS = {
    "firebase_analytics": ("Analytics", ["App interactions", "Device or other IDs"]),
    "firebase_crashlytics": ("Crash reporting", ["Crash logs", "Diagnostics", "Device or other IDs"]),
    "firebase_messaging": ("Push messaging", ["Device or other IDs"]),
    "firebase_auth": ("Authentication", ["Email address", "User IDs"]),
    "cloud_firestore": ("Cloud database", ["Depends on stored data"]),
    "firebase_storage": ("Cloud file storage", ["Depends on stored data"]),
    "firebase_performance": ("Performance monitoring", ["Diagnostics"]),
    "google_mobile_ads": ("Advertising", ["Device or other IDs", "App interactions", "Location: approximate"]),
    "google_sign_in": ("Authentication", ["Email address", "Name", "User IDs"]),
    "supabase_flutter": ("Backend / auth", ["Email address", "User IDs", "Depends on stored data"]),
    "sentry_flutter": ("Crash reporting", ["Crash logs", "Diagnostics"]),
    "facebook_app_events": ("Analytics / ads", ["App interactions", "Device or other IDs"]),
    "flutter_facebook_auth": ("Authentication", ["Email address", "Name", "User IDs"]),
    "onesignal_flutter": ("Push messaging", ["Device or other IDs"]),
    "amplitude_flutter": ("Analytics", ["App interactions", "Device or other IDs"]),
    "mixpanel_flutter": ("Analytics", ["App interactions", "Device or other IDs"]),
    "appsflyer_sdk": ("Attribution", ["Device or other IDs", "App interactions"]),
    "adjust_sdk": ("Attribution", ["Device or other IDs", "App interactions"]),
    "geolocator": ("Location", ["Location: precise"]),
    "location": ("Location", ["Location: precise"]),
    "image_picker": ("Media access", ["Photos and videos"]),
    "camera": ("Camera", ["Photos and videos"]),
    "flutter_contacts": ("Contacts", ["Contacts"]),
    "contacts_service": ("Contacts", ["Contacts"]),
    "in_app_purchase": ("Payments", ["Purchase history"]),
    "purchases_flutter": ("Subscriptions", ["Purchase history", "User IDs"]),
    "health": ("Health data", ["Health info", "Fitness info"]),
}
ADS_OR_ANALYTICS = {"google_mobile_ads", "firebase_analytics", "facebook_app_events", "appsflyer_sdk",
                    "adjust_sdk", "amplitude_flutter", "mixpanel_flutter"}
CONSENT_SDKS = {"google_mobile_ads"}  # ships the UMP consent API


def permission_inventory(app: AppContext) -> list[dict]:
    found = {}
    manifests = android_manifests(app.root)
    merged = sorted((app.root / "build" / "app" / "intermediates").glob("merged_manifest*/**/AndroidManifest.xml")) \
        if (app.root / "build").is_dir() else []
    for manifest in manifests + merged:
        text = read_text(manifest)
        if text is None:
            continue
        for element in manifest_permissions(text):
            name = element["name"]
            short = name.replace("android.permission.", "")
            risk, categories = PERMISSIONS.get(short, ("unknown", []))
            entry = found.setdefault(name, {"permission": name, "risk": risk, "data_categories": categories,
                                            "sources": [], "removed": False})
            entry["sources"].append(str(manifest.relative_to(app.root)))
            if element["removed"]:
                entry["removed"] = True
    return sorted(found.values(), key=lambda p: p["permission"])


def sdk_inventory(app: AppContext) -> list[dict]:
    packages = lock_packages(app.root)
    return [{"package": name, "version": packages[name].get("version"), "purpose": SDKS[name][0],
             "data_categories": SDKS[name][1], "direct": packages[name].get("dependency", "").startswith("direct")}
            for name in sorted(packages) if name in SDKS]


def inferred_categories(permissions, sdks) -> set[str]:
    categories = set()
    for item in permissions:
        if not item["removed"]:
            categories.update(item["data_categories"])
    for item in sdks:
        categories.update(item["data_categories"])
    categories.discard("Depends on stored data")
    return categories


def _declared(config) -> dict:
    privacy = config.get("privacy") or {}
    declared = privacy.get("data_types") or privacy.get("data_collected") or []
    return {"categories": set(declared) if isinstance(declared, list) else set(),
            "policy_url": privacy.get("policy_url") or (config.get("store") or {}).get("privacy_policy_url", ""),
            "deletion_url": privacy.get("account_deletion_url", ""),
            "retention": privacy.get("retention_policy", "NOT DEFINED"),
            "consent": privacy.get("consent_required", "NOT REVIEWED"),
            "consent_mechanism": privacy.get("consent_mechanism", "")}


def check_url(url, opener=urllib.request.urlopen, timeout=10) -> bool:
    try:
        request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "MyAppFactory-privacy-check"})
        with opener(request, timeout=timeout) as response:
            return 200 <= response.status < 400
    except (urllib.error.URLError, OSError, ValueError):
        return False


def data_safety_draft(app, permissions, sdks, declared) -> dict:
    categories = sorted(inferred_categories(permissions, sdks) | declared["categories"])
    return {"status": "DRAFT — requires human review", "app_id": app.app_id,
            "data_types": [{"category": c,
                            "collected": True,
                            "shared": any(c in s["data_categories"] for s in sdks
                                          if s["purpose"] in ("Advertising", "Attribution", "Analytics / ads")),
                            "sources": sorted({s["package"] for s in sdks if c in s["data_categories"]}
                                              | {p["permission"] for p in permissions if c in p["data_categories"]}),
                            "purposes": "REVIEW", "optional": "REVIEW", "encrypted_in_transit": "REVIEW"}
                           for c in categories],
            "account_deletion_url": declared["deletion_url"] or None,
            "note": "Inferred from SDKs and permissions. Your actual data practices decide the declaration."}


def run_privacy(app: AppContext, execute=False, opener=urllib.request.urlopen) -> dict:
    config = load_app_config(app.root)
    permissions = permission_inventory(app)
    sdks = sdk_inventory(app)
    declared = _declared(config)
    inferred = inferred_categories(permissions, sdks)
    auth = ((config.get("integrations") or {}).get("authentication") or {}).get("enabled") \
        or any(s["purpose"].startswith("Authentication") for s in sdks)
    checks = []
    high = [p["permission"] for p in permissions if p["risk"] == "high" and not p["removed"]]
    checks.append(R.check("Permission inventory", R.WARN if high else R.PASS,
                          f"{len(permissions)} permission(s); high-risk: {', '.join(high) or 'none'}"))
    checks.append(R.check("Third-party SDK inventory", R.PASS, f"{len(sdks)} data-relevant SDK(s): "
                          + (", ".join(s["package"] for s in sdks) or "none")))
    undeclared = sorted(inferred - declared["categories"])
    checks.append(R.check("Declared vs inferred data collection",
                          R.FAIL if undeclared and declared["categories"] else (R.WARN if undeclared else R.PASS),
                          f"Not declared in APP_CONFIG privacy.data_types: {', '.join(undeclared)}" if undeclared
                          else "Declarations cover inferred categories"))
    needs_policy = bool(inferred or auth)
    url = declared["policy_url"]
    if not url:
        checks.append(R.check("Privacy policy URL", R.FAIL if needs_policy else R.WARN, "Not set (privacy.policy_url)"))
    elif not url.startswith("https://"):
        checks.append(R.check("Privacy policy URL", R.FAIL, "Must be an https:// URL"))
    elif execute:
        checks.append(R.check("Privacy policy URL", R.PASS if check_url(url, opener) else R.FAIL, "Reachability checked"))
    else:
        checks.append(R.check("Privacy policy URL", R.NOT_RUN, "Set; pass --execute to check reachability"))
    if auth:
        checks.append(R.check("Account deletion readiness", R.PASS if declared["deletion_url"] else R.FAIL,
                              "Deletion URL declared" if declared["deletion_url"]
                              else "Apps with accounts need an in-app and web deletion path (privacy.account_deletion_url)"))
    else:
        checks.append(R.check("Account deletion readiness", R.NOT_APPLICABLE, "No user accounts detected"))
    tracking = {s["package"] for s in sdks} & ADS_OR_ANALYTICS
    if tracking:
        has_consent = bool({s["package"] for s in sdks} & CONSENT_SDKS) or bool(declared["consent_mechanism"])
        checks.append(R.check("Consent configuration", R.PASS if has_consent and declared["consent_mechanism"] else R.WARN,
                              f"Tracking SDKs: {', '.join(sorted(tracking))}; mechanism: "
                              f"{declared['consent_mechanism'] or 'not declared (privacy.consent_mechanism)'}"))
    else:
        checks.append(R.check("Consent configuration", R.NOT_APPLICABLE, "No ads/analytics SDKs"))
    checks.append(R.check("Data retention documented",
                          R.WARN if declared["retention"] in ("", "NOT DEFINED") else R.PASS,
                          declared["retention"] or "NOT DEFINED"))
    draft = data_safety_draft(app, permissions, sdks, declared)
    store = ApprovalStore.for_app(app)
    signed = [a for a in store.list("CONSUMED") + store.list("APPROVED") if a["action"] == "privacy_declaration"]
    current_hash = payload_hash(draft["data_types"])
    signed_current = any(a["payload_hash"] == current_hash for a in signed)
    checks.append(R.check("Data Safety declaration sign-off", R.PASS if signed_current else R.MANUAL,
                          "Human sign-off recorded for this exact draft" if signed_current
                          else "Review the draft, then request sign-off with `privacy signoff`"))
    return R.make_report(app, "privacy", "Privacy & data protection", checks, milestone=44,
                         data={"permissions": permissions, "sdks": sdks, "inferred_categories": sorted(inferred),
                               "declared_categories": sorted(declared["categories"]), "data_safety_draft": draft,
                               "draft_hash": current_hash},
                         limitations=["Not legal advice and not a compliance determination.",
                                      "SDK data categories are typical defaults; confirm with each SDK's disclosure.",
                                      "Check current Google Play Data Safety and User Data policy before submission."],
                         manual=["Confirm what each SDK actually collects with your configuration.",
                                 "Confirm the privacy policy matches the declarations.",
                                 "Enter the Data Safety form in Play Console yourself."])


def request_signoff(app: AppContext, report: dict) -> dict:
    """Create (or consume) a privacy_declaration approval bound to the current draft."""
    return ApprovalStore.for_app(app).request(
        "privacy_declaration", report["data"]["data_safety_draft"]["data_types"],
        reason="Human review of Data Safety draft", requested_by="privacy-tool")


def retention_template(app: AppContext, report: dict) -> str:
    lines = [f"# Data retention — {app.name} ({app.app_id})", "", "DRAFT — complete and review before publishing.", "",
             "| Data category | Where stored | Retention period | Deletion method |", "|---|---|---|---|"]
    for category in report["data"]["inferred_categories"] or ["(none inferred)"]:
        lines.append(f"| {category} | REVIEW | REVIEW | REVIEW |")
    return "\n".join(lines) + "\n"
