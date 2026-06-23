[app]
# (str) Title of your application
title = JARVIS Core OS

# (str) Package name
package.name = jarvis_core

# (str) Package domain (needed for android packaging)
package.domain = org.assistant.jarvis

# (str) Source code where the main.py lives
source.dir = .

# (str) Version of your application
version = 1.0.0

# (list) Source files to include
source.include_exts = py,png,jpg,jpeg,html,css,js

# (list) Application requirements (Crucial: pyjnius and android are now included)
requirements = python3,flask,pyjnius,android,PyPDF2,jinja2,werkzeug,click,itsdangerous

# (str) Supported orientations (landscape, portrait or all)
orientation = portrait

# (bool) Use fullscreen mode
fullscreen = 1

# ==============================================================================
# Android specific configurations
# ==============================================================================

# (list) Permissions requested by your app (Streamlined for Android 10)
# Change this from 33 to 29 (matches Android 10 legacy storage defaults)
android.api = 29

# Ensure these base permissions are declared
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE
# (int) Minimum API required
android.minapi = 21

# (bool) Accept SDK license
android.accept_sdk_license = True

# (str) Android archs to build for
android.archs = arm64-v8a

# (str) Application arguments injected into AndroidManifest.xml
#android.manifest.application_arguments = android:requestLegacyExternalStorage="true" android:usesCleartextTraffic="true"

# --- Python-for-Android WebView Setup ---

# (str) Bootstrap to use (webview is required for Flask)
p4a.bootstrap = webview

# (int) Port where the flask server will run
p4a.port = 5000

# ==============================================================================
# Buildozer configurations
# ==============================================================================

[buildozer]
# (int) Log level (0 = error only, 1 = info, 2 = debug)
log_level = 2

# (int) Display warning if buildozer is run as root
warn_on_root = 1
