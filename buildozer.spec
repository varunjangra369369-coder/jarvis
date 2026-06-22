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

# (list) Source files to include (add extensions you are using)
source.include_exts = py,png,jpg,jpeg,html,css,js

# (list) Application requirements
requirements = python3,flask,PyPDF2,jinja2,werkzeug,click,itsdangerous

# (str) Supported orientations (landscape, portrait or all)
orientation = portrait

# (bool) Use fullscreen mode
fullscreen = 1

# --- Android Specific ---

# (list) Permissions requested by your app
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

# (int) Target Android SDK
android.api = 33

# (int) Minimum API required
android.minapi = 21

# (bool) Accept SDK license
android.accept_sdk_license = True

# (str) Android archs to build for
android.archs = arm64-v8a

# (bool) Request legacy external storage access
android.manifest.application_arguments = android:requestLegacyExternalStorage="true"

# --- Python-for-Android WebView Setup ---

# (str) Bootstrap to use (webview is required for Flask)
p4a.bootstrap = webview

# (int) Port where the flask server will run
p4a.port = 5000
