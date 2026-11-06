import java.io.File

plugins {
    id("com.android.application")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

val releaseSigningEnabled =
    System.getenv("MYAPP_RELEASE_SIGNING_ENABLED")?.equals("true", ignoreCase = true) == true
val releaseSigningStoreFile = System.getenv("MYAPP_RELEASE_STORE_FILE")?.takeIf(String::isNotBlank)
val releaseSigningStorePassword = System.getenv("MYAPP_RELEASE_STORE_PASSWORD")?.takeIf(String::isNotBlank)
val releaseSigningKeyAlias = System.getenv("MYAPP_RELEASE_KEY_ALIAS")?.takeIf(String::isNotBlank)
val releaseSigningKeyPassword = System.getenv("MYAPP_RELEASE_KEY_PASSWORD")?.takeIf(String::isNotBlank)
val releaseSigningConfigured =
    releaseSigningEnabled &&
        releaseSigningStoreFile != null &&
        releaseSigningStorePassword != null &&
        releaseSigningKeyAlias != null &&
        releaseSigningKeyPassword != null &&
        File(releaseSigningStoreFile).isAbsolute &&
        File(releaseSigningStoreFile).isFile
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

    val keystore = File(releaseSigningStoreFile!!)
    if (!keystore.isAbsolute || !keystore.isFile) {
        throw GradleException(
            "MYAPP_RELEASE_STORE_FILE must point to an existing absolute keystore file."
        )
    }
}

android {
    namespace = "com.example.nova_ui"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "com.example.nova_ui"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    signingConfigs {
        if (releaseSigningConfigured) {
            create("release") {
                storeFile = File(releaseSigningStoreFile!!)
                storePassword = releaseSigningStorePassword!!
                keyAlias = releaseSigningKeyAlias!!
                keyPassword = releaseSigningKeyPassword!!
            }
        }
    }

    buildTypes {
        release {
            if (releaseSigningConfigured) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}

flutter {
    source = "../.."
}
