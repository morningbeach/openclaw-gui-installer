"""
py2app setup for OpenClaw Menu Bar app
Build:  python3 setup_menubar.py py2app
"""
from setuptools import setup

APP = ["menubar_app.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "CFBundleName": "OpenClaw Menu Bar",
        "CFBundleDisplayName": "OpenClaw Menu Bar",
        "CFBundleIdentifier": "ai.openclaw.menubar",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0",
        "LSUIElement": True,  # Hide from Dock — menu bar only
        "LSMinimumSystemVersion": "12.0",
        "NSHumanReadableCopyright": "© 2025 OpenClaw",
    },
    "packages": ["rumps"],
    "includes": ["objc", "Foundation", "AppKit"],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
