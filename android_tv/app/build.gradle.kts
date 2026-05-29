plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.miai.love.tv"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.miai.love.tv"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0"

        buildConfigField("String", "DEFAULT_SCREEN_URL", "\"http://10.0.2.2:5180/web#/screen/player\"")
    }

    buildFeatures {
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildTypes {
        debug {
            applicationIdSuffix = ".debug"
            buildConfigField("Boolean", "DEBUG_PANEL_ENABLED", "true")
        }
        release {
            isMinifyEnabled = false
            buildConfigField("Boolean", "DEBUG_PANEL_ENABLED", "true")
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
}

dependencies {
    implementation("androidx.media3:media3-exoplayer:1.4.1")
    implementation("androidx.media3:media3-ui:1.4.1")
}
