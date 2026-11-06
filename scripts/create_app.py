#!/usr/bin/env python3
"""Safely create a Nova UI Flutter app with fresh Android platform scaffolding."""
from pathlib import Path
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
STARTER = ROOT / "templates" / "nova_ui_flutter_starter"
STARTER_PACKAGE = "nova_ui"
PACKAGE_RE = re.compile(r"^[a-z][a-z0-9]{0,62}(\.[a-z][a-z0-9_]{0,62})+$")
COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
EXCLUDED_NAMES = {
    ".dart_tool", ".gradle", ".metadata", ".packages", ".pub", "build",
    ".flutter-plugins", ".flutter-plugins-dependencies", "local.properties",
    "coverage", "key.properties", "google-services.json",
    "GoogleService-Info.plist",
}


def is_excluded_file(name):
    return (
        name in EXCLUDED_NAMES
        or Path(name).suffix in {".iml", ".jks", ".keystore"}
        or name == ".env"
        or (name.startswith(".env.") and name != ".env.example")
    )


def ignore_generated(_directory, names):
    linked = [
        name for name in names
        if (Path(_directory) / name).is_symlink()
    ]
    if linked:
        raise ValueError(
            "Refusing to copy starter symlink(s): " + ", ".join(sorted(linked))
        )
    return {name for name in names if is_excluded_file(name)}


def copy_starter(source, target):
    return shutil.copytree(source, target, ignore=ignore_generated)


def update_package_imports(target, package_name):
    for directory in ("lib", "test"):
        folder = target / directory
        if not folder.is_dir():
            continue
        for path in folder.rglob("*.dart"):
            content = path.read_text(encoding="utf-8")
            updated = content.replace(
                f"package:{STARTER_PACKAGE}/",
                f"package:{package_name}/",
            )
            if updated != content:
                path.write_text(updated, encoding="utf-8")


def app_config(name, package, version, primary_color, min_sdk, target_sdk):
    return {
        "schema_version": 2,
        "app": {
            "name": name,
            "package_name": package,
            "version": version,
            "platform": "android",
            "project_type": "new",
        },
        "branding": {
            "primary_color": primary_color,
            "launcher_icon": {"status": "FLUTTER_DEFAULT", "source": ""},
            "splash_screen": {"status": "FLUTTER_DEFAULT", "source": ""},
            "store_icon": {"status": "NOT PROVIDED", "source": ""},
        },
        "architecture": {
            "style": "layered",
            "state_management": "Provider",
            "navigation": "Flutter Navigator",
            "persistence": "none",
            "routing": "Flutter Navigator",
            "storage": "none",
            "layers": ["presentation", "application", "domain", "data"],
        },
        "integrations": {
            "authentication": {"enabled": False, "provider": "none"},
            "backend": "none",
            "apis": [],
            "notifications": {"enabled": False},
            "analytics": {"enabled": False, "provider": "none"},
            "crash_reporting": {"enabled": False, "provider": "none"},
        },
        "environments": {
            environment: {
                "api_base_url": "",
                "required_variables": [],
            }
            for environment in ("development", "staging", "production")
        },
        "feature_flags": {},
        "design": {
            "system": "Nova UI",
            "theme": "NovaBrandTheme",
            "locales": ["en"],
        },
        "privacy": {
            "data_collection": "NOT REVIEWED",
            "consent_required": "NOT REVIEWED",
            "retention_policy": "NOT DEFINED",
        },
        "permissions": [],
        "build": {
            "android": {
                "application_id": package,
                "min_sdk": min_sdk if min_sdk is not None else "flutter.minSdkVersion",
                "target_sdk": target_sdk if target_sdk is not None else "flutter.targetSdkVersion",
                "gradle_flavors": ["development", "staging", "production"],
                "compile_sdk": "flutter.compileSdkVersion",
                "kotlin_jvm_target": 17,
            },
        },
        "store": {
            "title": name,
            "short_description": "",
            "full_description": "",
            "assets": {
                "icon": "NOT PROVIDED",
                "feature_graphic": "NOT PROVIDED",
                "phone_screenshots": "NOT CAPTURED",
            },
        },
        "release": {
            "signing": "NOT CONFIGURED",
            "upload": "NOT AUTHORIZED",
            "publish": "NOT AUTHORIZED",
        },
    }


def _replace_exactly_once(text, pattern, replacement, description):
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"Could not safely update generated Android {description}")
    return updated


def _gradle_string(value):
    return json.dumps(value, ensure_ascii=True).replace("$", "\\$")


def _release_signing_guard_kts():
    return """val releaseSigningEnabled =
    System.getenv("MYAPP_RELEASE_SIGNING_ENABLED")?.equals("true", ignoreCase = true) == true
val releaseSigningStoreFile = System.getenv("MYAPP_RELEASE_STORE_FILE")?.takeIf(String::isNotBlank)
val releaseSigningStorePassword = System.getenv("MYAPP_RELEASE_STORE_PASSWORD")?.takeIf(String::isNotBlank)
val releaseSigningKeyAlias = System.getenv("MYAPP_RELEASE_KEY_ALIAS")?.takeIf(String::isNotBlank)
val releaseSigningKeyPassword = System.getenv("MYAPP_RELEASE_KEY_PASSWORD")?.takeIf(String::isNotBlank)
val releaseSigningKeystore = releaseSigningStoreFile?.let { File(it) }
val releaseSigningConfigured =
    releaseSigningEnabled &&
        releaseSigningStorePassword != null &&
        releaseSigningKeyAlias != null &&
        releaseSigningKeyPassword != null &&
        releaseSigningKeystore?.isAbsolute == true &&
        releaseSigningKeystore.isFile
val releaseBuildRequested = gradle.startParameter.taskNames.any { taskName ->
    taskName.substringAfterLast(':').lowercase().matches(
        Regex("(assemble|bundle|package|validatesigning)([a-z0-9]+)?release")
    )
}

if (releaseBuildRequested) {
    val requiredVariables = mapOf(
        "MYAPP_RELEASE_SIGNING_ENABLED" to releaseSigningEnabled,
        "MYAPP_RELEASE_STORE_FILE" to (releaseSigningStoreFile != null),
        "MYAPP_RELEASE_STORE_PASSWORD" to (releaseSigningStorePassword != null),
        "MYAPP_RELEASE_KEY_ALIAS" to (releaseSigningKeyAlias != null),
        "MYAPP_RELEASE_KEY_PASSWORD" to (releaseSigningKeyPassword != null),
    )
    val missingVariables = requiredVariables.filterValues { !it }.keys
    if (missingVariables.isNotEmpty()) {
        throw GradleException(
            "Release signing is not configured. Set: ${missingVariables.joinToString(", ")}."
        )
    }

    if (releaseSigningKeystore?.isAbsolute != true || releaseSigningKeystore?.isFile != true) {
        throw GradleException(
            "MYAPP_RELEASE_STORE_FILE must point to an existing absolute keystore file."
        )
    }
}
"""


def _release_signing_guard_groovy():
    return """def releaseSigningEnabled = System.getenv('MYAPP_RELEASE_SIGNING_ENABLED')?.equalsIgnoreCase('true')
def releaseSigningStoreFile = System.getenv('MYAPP_RELEASE_STORE_FILE')?.trim()
def releaseSigningStorePassword = System.getenv('MYAPP_RELEASE_STORE_PASSWORD')?.trim()
def releaseSigningKeyAlias = System.getenv('MYAPP_RELEASE_KEY_ALIAS')?.trim()
def releaseSigningKeyPassword = System.getenv('MYAPP_RELEASE_KEY_PASSWORD')?.trim()
def releaseSigningKeystore = releaseSigningStoreFile ? new File(releaseSigningStoreFile) : null
def releaseSigningConfigured = releaseSigningEnabled &&
        releaseSigningStorePassword && releaseSigningKeyAlias && releaseSigningKeyPassword &&
        releaseSigningKeystore?.isAbsolute() && releaseSigningKeystore?.isFile()
def releaseBuildRequested = gradle.startParameter.taskNames.any { taskName ->
    taskName.tokenize(':').last().toLowerCase() ==~ /(assemble|bundle|package|validatesigning)([a-z0-9]+)?release/
}

if (releaseBuildRequested) {
    def requiredVariables = [
        'MYAPP_RELEASE_SIGNING_ENABLED': releaseSigningEnabled,
        'MYAPP_RELEASE_STORE_FILE': releaseSigningStoreFile,
        'MYAPP_RELEASE_STORE_PASSWORD': releaseSigningStorePassword,
        'MYAPP_RELEASE_KEY_ALIAS': releaseSigningKeyAlias,
        'MYAPP_RELEASE_KEY_PASSWORD': releaseSigningKeyPassword,
    ]
    def missingVariables = requiredVariables.findAll { key, value -> !value }.keySet()
    if (missingVariables) {
        throw new GradleException("Release signing is not configured. Set: ${missingVariables.join(', ')}.")
    }
    if (!releaseSigningKeystore.isAbsolute() || !releaseSigningKeystore.isFile()) {
        throw new GradleException(
            'MYAPP_RELEASE_STORE_FILE must point to an existing absolute keystore file.'
        )
    }
}
"""


def configure_android(android, package, name, min_sdk=None, target_sdk=None):
    gradle_files = [
        android / "app" / "build.gradle.kts",
        android / "app" / "build.gradle",
    ]
    gradle = next((path for path in gradle_files if path.is_file()), None)
    if gradle is None:
        raise ValueError("Flutter scaffold did not generate an Android app Gradle file")
    text = gradle.read_text(encoding="utf-8")
    text = _replace_exactly_once(
        text,
        r'^(\s*namespace\s*=\s*)"[^"]+"',
        rf'\g<1>"{package}"',
        "namespace",
    ) if gradle.suffix == ".kts" else _replace_exactly_once(
        text,
        r'^(\s*namespace\s*)"[^"]+"',
        rf'\g<1>"{package}"',
        "namespace",
    )
    text = _replace_exactly_once(
        text,
        r'^(\s*applicationId\s*=\s*)"[^"]+"',
        rf'\g<1>"{package}"',
        "applicationId",
    ) if gradle.suffix == ".kts" else _replace_exactly_once(
        text,
        r'^(\s*applicationId\s*)"[^"]+"',
        rf'\g<1>"{package}"',
        "applicationId",
    )
    if "buildFeatures {" not in text:
        feature_setting = "resValues = true" if gradle.suffix == ".kts" else "resValues true"
        text, count = re.subn(
            r"(?m)^(android\s*\{\s*)$",
            r"\1\n    buildFeatures {\n        " + feature_setting + r"\n    }\n",
            text,
            count=1,
        )
        if count != 1:
            raise ValueError("Could not safely enable Android flavor resource values")
    if min_sdk is not None:
        text = _replace_exactly_once(
            text,
            r"^(\s*minSdk\s*=\s*)flutter\.minSdkVersion\b"
            if gradle.suffix == ".kts"
            else r"^(\s*minSdk\s+)flutter\.minSdkVersion\b",
            rf"\g<1>{min_sdk}", "minimum SDK")
    if target_sdk is not None:
        text = _replace_exactly_once(
            text,
            r"^(\s*targetSdk\s*=\s*)flutter\.targetSdkVersion\b"
            if gradle.suffix == ".kts"
            else r"^(\s*targetSdk\s+)flutter\.targetSdkVersion\b",
            rf"\g<1>{target_sdk}", "target SDK")
    if "productFlavors {" not in text:
        escaped_name = _gradle_string(name)
        if gradle.suffix == ".kts":
            flavor_block = (
                '    flavorDimensions += "environment"\n'
                "    productFlavors {\n"
                '        create("development") {\n'
                '            dimension = "environment"\n'
                '            applicationIdSuffix = ".dev"\n'
                f'            resValue("string", "app_name", {_gradle_string(name + " (Development)")})\n'
                "        }\n"
                '        create("staging") {\n'
                '            dimension = "environment"\n'
                '            applicationIdSuffix = ".staging"\n'
                f'            resValue("string", "app_name", {_gradle_string(name + " (Staging)")})\n'
                "        }\n"
                '        create("production") {\n'
                '            dimension = "environment"\n'
                f'            resValue("string", "app_name", {escaped_name})\n'
                "        }\n"
                "    }\n\n"
            )
        else:
            flavor_block = (
                '    flavorDimensions "environment"\n'
                "    productFlavors {\n"
                "        development {\n"
                '            dimension "environment"\n'
                '            applicationIdSuffix ".dev"\n'
                f'            resValue "string", "app_name", {_gradle_string(name + " (Development)")}\n'
                "        }\n"
                "        staging {\n"
                '            dimension "environment"\n'
                '            applicationIdSuffix ".staging"\n'
                f'            resValue "string", "app_name", {_gradle_string(name + " (Staging)")}\n'
                "        }\n"
                "        production {\n"
                '            dimension "environment"\n'
                f'            resValue "string", "app_name", {escaped_name}\n'
                "        }\n"
                "    }\n\n"
            )
        text, count = re.subn(
            r"(?m)^(    buildTypes\s*\{)",
            flavor_block + r"\1",
            text,
            count=1,
        )
        if count != 1:
            raise ValueError("Could not safely add Android environment product flavors")
    text = re.sub(
        r"(?m)^\s*signingConfig\s*(?:=\s*signingConfigs\.getByName\(\"debug\"\)|signingConfigs\.debug)\s*\n",
        "",
        text,
    )
    if "Release signing is not configured." not in text:
        if gradle.suffix == ".kts" and not text.startswith("import java.io.File"):
            text = "import java.io.File\n\n" + text
        guard = (
            _release_signing_guard_kts()
            if gradle.suffix == ".kts"
            else _release_signing_guard_groovy()
        )
        text, count = re.subn(
            r"(?m)^(android\s*\{)",
            guard + r"\n\1",
            text,
            count=1,
        )
        if count != 1:
            raise ValueError("Could not safely add Android release-signing guard")

    if "signingConfigs {" not in text:
        if gradle.suffix == ".kts":
            signing_configs = """    signingConfigs {
        if (releaseSigningConfigured) {
            create("release") {
                storeFile = File(releaseSigningStoreFile!!)
                storePassword = releaseSigningStorePassword!!
                keyAlias = releaseSigningKeyAlias!!
                keyPassword = releaseSigningKeyPassword!!
            }
        }
    }

"""
        else:
            signing_configs = """    signingConfigs {
        if (releaseSigningConfigured) {
            release {
                storeFile file(releaseSigningStoreFile)
                storePassword releaseSigningStorePassword
                keyAlias releaseSigningKeyAlias
                keyPassword releaseSigningKeyPassword
            }
        }
    }

"""
        text, count = re.subn(
            r"(?m)^(    buildTypes\s*\{)",
            signing_configs + r"\1",
            text,
            count=1,
        )
        if count != 1:
            raise ValueError("Could not safely add Android release signing configuration")
    release_signing = (
        '            if (releaseSigningConfigured) {\n'
        '                signingConfig = signingConfigs.getByName("release")\n'
        '            }\n'
        if gradle.suffix == ".kts"
        else '            if (releaseSigningConfigured) {\n'
        '                signingConfig signingConfigs.release\n'
        '            }\n'
    )
    text, count = re.subn(
        r"(?m)^(\s*release\s*\{\s*)",
        lambda match: match.group(1) + release_signing,
        text,
        count=1,
    )
    if count != 1:
        raise ValueError("Could not safely configure Android release signing")
    gradle.write_text(text, encoding="utf-8")

    manifest = android / "app" / "src" / "main" / "AndroidManifest.xml"
    if not manifest.is_file():
        raise ValueError("Flutter scaffold did not generate the Android main manifest")
    manifest_text = manifest.read_text(encoding="utf-8")
    manifest_text, count = re.subn(
        r'android:label="[^"]+"',
        'android:label="@string/app_name"',
        manifest_text,
        count=1,
    )
    if count != 1:
        raise ValueError("Could not safely set the Android app display-name resource")
    manifest.write_text(manifest_text, encoding="utf-8")

    kotlin_root = android / "app" / "src" / "main" / "kotlin"
    activities = list(kotlin_root.rglob("MainActivity.kt")) if kotlin_root.is_dir() else []
    if len(activities) != 1:
        raise ValueError("Expected exactly one generated Kotlin MainActivity")
    activity = activities[0]
    activity_text = activity.read_text(encoding="utf-8")
    activity_text, count = re.subn(
        r"(?m)^package\s+[\w.]+\s*$",
        f"package {package}",
        activity_text,
        count=1,
    )
    if count != 1:
        raise ValueError("Could not safely set the Android activity package")
    destination = kotlin_root.joinpath(*package.split("."), "MainActivity.kt")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(activity_text, encoding="utf-8")
    activity.unlink()
    for parent in activity.parents:
        if parent == kotlin_root:
            break
        try:
            parent.rmdir()
        except OSError:
            break


def generate_android_scaffold(directory, package, project_name, app_name, min_sdk=None, target_sdk=None):
    flutter = shutil.which("flutter")
    if not flutter:
        raise RuntimeError("Flutter executable not found; Android scaffolding was not generated")
    organization = ".".join(package.split(".")[:-1])
    generated = directory / "android_scaffold"
    command = [
        flutter, "create", "--no-pub", "--platforms=android",
        f"--org={organization}", f"--project-name={project_name}",
        "--android-language=kotlin", str(generated),
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=180, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Flutter Android scaffolding timed out after 180 seconds") from exc
    except OSError as exc:
        raise RuntimeError(f"Unable to execute Flutter scaffolding: {exc}") from exc
    if result.returncode:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            f"Flutter Android scaffolding failed (exit {result.returncode}):\n{details[-4000:]}")
    android = generated / "android"
    if not android.is_dir():
        raise RuntimeError("Flutter reported success but generated no android/ directory")
    configure_android(android, package, app_name, min_sdk, target_sdk)
    return android


def write_environment_config(project):
    config_dir = project / "lib" / "core" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "app_environment.dart").write_text(
        """enum AppEnvironment {
  development,
  staging,
  production;

  static const _configuredName = String.fromEnvironment(
    'APP_ENV',
    defaultValue: 'development',
  );

  static AppEnvironment parse(String value) => switch (value) {
        'development' => AppEnvironment.development,
        'staging' => AppEnvironment.staging,
        'production' => AppEnvironment.production,
        _ => throw ArgumentError.value(value, 'APP_ENV', 'Unknown environment'),
      };

  static final current = parse(_configuredName);
  static const apiBaseUrl = String.fromEnvironment('API_BASE_URL');
  static const diagnosticsEnabled =
      bool.fromEnvironment('ENABLE_DIAGNOSTICS', defaultValue: false);
}
""",
        encoding="utf-8",
    )


def configure_dart_branding(project, name, primary_color):
    main = project / "lib" / "main.dart"
    if not main.is_file():
        raise ValueError("Nova UI starter is missing lib/main.dart")
    text = main.read_text(encoding="utf-8")
    text, title_count = re.subn(
        r"title:\s*'Nova UI'",
        f"title: {json.dumps(name, ensure_ascii=True)}",
        text,
        count=1,
    )
    text, light_count = re.subn(
        r"theme:\s*NovaTheme\.light\(\)",
        f"theme: NovaBrandTheme.light(const Color(0xFF{primary_color[1:]}))",
        text,
        count=1,
    )
    text, dark_count = re.subn(
        r"darkTheme:\s*NovaTheme\.dark\(\)",
        f"darkTheme: NovaBrandTheme.dark(const Color(0xFF{primary_color[1:]}))",
        text,
        count=1,
    )
    if (title_count, light_count, dark_count) != (1, 1, 1):
        raise ValueError("Could not safely apply app name and brand color to Nova UI")
    text = text.replace(
        "import 'core/design_system/nova_theme.dart';\n",
        "import 'core/design_system/nova_brand_theme.dart';\n",
    )
    main.write_text(text, encoding="utf-8")


def make_store_inventory(project, app_name):
    inventory = {
        "schema_version": 1,
        "app_name": app_name,
        "status": "NEEDS APP-SPECIFIC ASSETS AND REVIEW",
        "assets": [
            {"asset": "store_icon_512.png", "status": "NOT PROVIDED"},
            {"asset": "feature_graphic_1024x500.png", "status": "NOT PROVIDED"},
            {"asset": "phone_screenshot_1.png", "status": "NOT CAPTURED"},
            {"asset": "phone_screenshot_2.png", "status": "NOT CAPTURED"},
        ],
        "note": "The factory does not invent app-specific artwork or claim store readiness.",
    }
    (project / "STORE_ASSET_INVENTORY.json").write_text(
        json.dumps(inventory, indent=2) + "\n", encoding="utf-8")


def validate_request(name, package, target, min_sdk, target_sdk, primary_color, version):
    name = name.strip()
    package = package.strip()
    if not name or len(name) > 50:
        raise ValueError("App name must contain 1–50 non-whitespace characters")
    if not PACKAGE_RE.fullmatch(package):
        raise ValueError("Package must be lowercase reverse-domain identifiers (for example com.dev.factorytest)")
    if not COLOR_RE.fullmatch(primary_color):
        raise ValueError("Primary color must be a six-digit hex value such as #6366F1")
    if min_sdk is not None and min_sdk < 21:
        raise ValueError("Android min SDK must be at least 21")
    if target_sdk is not None and target_sdk < (min_sdk or 21):
        raise ValueError("Android target SDK must be greater than or equal to min SDK")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+\+[1-9][0-9]*", version):
        raise ValueError("Version must use major.minor.patch+positiveBuildNumber format")
    target = Path(target).expanduser().resolve()
    protected_roots = (
        ROOT.resolve(),
        STARTER.resolve(),
        (ROOT / "design_system" / "nova_ui_flutter").resolve(),
    )
    if target in protected_roots or any(
        root in target.parents for root in protected_roots[1:]
    ):
        raise ValueError(f"Refusing to create an app inside a protected factory source path: {target}")
    if target.exists():
        raise FileExistsError(f"Target already exists; refusing to overwrite: {target}")
    slug = re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_")
    if not slug or not re.fullmatch(r"[a-z][a-z0-9_]*", slug):
        raise ValueError("App name must produce a valid Dart package name")
    return name, package, target, slug


def create_app(name, package, target, min_sdk=None, target_sdk=None,
               primary_color="#6366F1", version="1.0.0+1"):
    name, package, target, slug = validate_request(
        name, package, target, min_sdk, target_sdk, primary_color, version)
    if not STARTER.is_dir():
        raise FileNotFoundError(f"Starter template not found: {STARTER}")

    target.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix=f".{target.name}.factory-create-",
        dir=target.parent,
    ) as temporary:
        work = Path(temporary)
        project = work / "project"
        copy_starter(STARTER, project)

        pubspec = project / "pubspec.yaml"
        content = pubspec.read_text(encoding="utf-8")
        content, count = re.subn(
            r"(?m)^name:\s*[A-Za-z0-9_]+\s*$", f"name: {slug}", content, count=1)
        if count != 1:
            raise ValueError("Could not safely update starter package name")
        content, count = re.subn(
            r"(?m)^version:\s*.*$", f"version: {version}", content, count=1)
        if count != 1:
            raise ValueError("Could not safely update starter version")
        content, count = re.subn(
            r"(?m)^description:.*$",
            f"description: {name} Flutter application.",
            content,
            count=1,
        )
        if count != 1:
            raise ValueError("Could not safely update starter description")
        pubspec.write_text(content, encoding="utf-8")
        update_package_imports(project, slug)
        configure_dart_branding(project, name, primary_color)

        readme = project / "README.md"
        if readme.exists():
            readme_text = readme.read_text(encoding="utf-8")
            readme_text, _ = re.subn(
                r"(?m)^# .*$", f"# {name}", readme_text, count=1)
            readme.write_text(readme_text, encoding="utf-8")

        android = generate_android_scaffold(
            work, package, slug, name, min_sdk, target_sdk)
        shutil.copytree(android, project / "android", ignore=ignore_generated)
        (project / ".metadata").unlink(missing_ok=True)
        (project / "pubspec.yaml").write_text(
            re.sub(r"(?m)^version:\s*.*$", f"version: {version}",
                   (project / "pubspec.yaml").read_text(encoding="utf-8"), count=1),
            encoding="utf-8",
        )
        # Flutter create may add its own default files; the Nova UI Dart app remains unchanged.
        config = app_config(
            name, package, version, primary_color, min_sdk, target_sdk)
        (project / "APP_CONFIG.json").write_text(
            json.dumps(config, indent=2) + "\n", encoding="utf-8")
        (project / "APP_FACTORY_METADATA.md").write_text(
            f"# App Factory Metadata\n\n- App name: {name}\n"
            f"- Dart package: `{slug}`\n- Android applicationId: `{package}` "
            "(production flavor)\n- Android namespace: `{package}`\n"
            f"- Version: `{version}`\n- Primary brand color: `{primary_color}`\n"
            "- Android scaffolding: generated with the installed Flutter SDK.\n"
            "- Environment flavors: development, staging, production. "
            "Development/staging use application ID suffixes `.dev`/`.staging`.\n"
            "- Match each Gradle flavor with `--dart-define=APP_ENV=<environment>`; "
            "provide non-secret API values with `--dart-define=API_BASE_URL=...`.\n"
            "- SDK levels use the installed Flutter toolchain defaults unless "
            "overridden in the creation command.\n"
            "- Default launcher icon and splash assets are Flutter-generated; "
            "replace with approved app artwork before release.\n"
            "- Signing, Firebase, AdMob and production credentials are not configured.\n",
            encoding="utf-8",
        )
        write_environment_config(project)
        make_store_inventory(project, name)
        (project / "ARCHITECTURE.md").write_text(
            "# Application architecture\n\n"
            "The starter uses a layered feature structure: presentation, application, "
            "domain and data. Keep domain code independent of Flutter and infrastructure; "
            "presentation code should depend on application/domain interfaces, not data "
            "implementations. See `scripts/architecture_audit.py` for static checks.\n",
            encoding="utf-8",
        )
        if target.exists():
            raise FileExistsError(f"Target appeared during generation; refusing to overwrite: {target}")
        os.rename(project, target)

    return {
        "target": str(target),
        "app_name": name,
        "dart_package": slug,
        "application_id": package,
        "namespace": package,
        "version": version,
        "android_scaffolded": True,
        "flavors": ["development", "staging", "production"],
        "files_copied": len(list(target.rglob("*"))),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Human-readable app name")
    parser.add_argument("--package", required=True, help="Reverse-domain Android package ID")
    parser.add_argument("--target", required=True, help="New destination folder")
    parser.add_argument("--min-sdk", type=int, help="Optional Android minimum SDK override")
    parser.add_argument("--target-sdk", type=int, help="Optional Android target SDK override")
    parser.add_argument("--primary-color", default="#6366F1")
    parser.add_argument("--version", default="1.0.0+1")
    parser.add_argument("--dry-run", action="store_true", help="Validate and preview without writing")
    args = parser.parse_args(argv)
    try:
        target = Path(args.target).expanduser()
        if not target.is_absolute():
            target = Path.cwd() / target
        name, package, target, _slug = validate_request(
            args.name, args.package, target,
            args.min_sdk, args.target_sdk, args.primary_color, args.version)
        if args.dry_run:
            print(json.dumps({
                "status": "DRY RUN",
                "name": name,
                "package": package,
                "target": str(target.resolve()),
                "android_scaffold": "flutter create --platforms=android",
                "flavors": ["development", "staging", "production"],
                "will_write_files": False,
            }, indent=2))
            return 0
        result = create_app(
            args.name, args.package, target,
            min_sdk=args.min_sdk,
            target_sdk=args.target_sdk,
            primary_color=args.primary_color,
            version=args.version,
        )
        print(json.dumps({"status": "CREATED", **result}, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
