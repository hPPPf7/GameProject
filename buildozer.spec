[app]
title = 菜鳥調查隊日誌
package.name = investigationdiary
package.domain = org.gameproject

source.dir = .
source.include_exts = py,json,png,jpg,jpeg,ttf,wav,mp3
source.include_patterns = assets/*,assets/**,data/*,data/**
source.exclude_dirs = .git,.venv,build,dist,release,__pycache__,assets/background

version = 0.1.1
orientation = portrait
fullscreen = 1

# Keep Android requirements narrow. This project is a pygame app and does not
# use Kivy/pyjnius; adding them makes the APK build compile unrelated native
# dependencies and currently breaks on GitHub Actions.
requirements = python3==3.10.12,hostpython3==3.10.12,pygame

presplash.filename = assets/start_background.png
icon.filename = assets/icon.png

android.permissions =
android.api = 35
android.minapi = 23
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
