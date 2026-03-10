"""
py2app setup for OpenClaw Installer
Build:  python3 setup.py py2app
"""

from setuptools import setup

APP = ["installer_gui.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "resources/openclaw.icns",
    "plist": {
        "CFBundleName": "OpenClaw Installer",
        "CFBundleDisplayName": "OpenClaw Installer",
        "CFBundleIdentifier": "ai.openclaw.installer",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0",
        "LSMinimumSystemVersion": "12.0",
        "NSHumanReadableCopyright": "© 2026 OpenClaw — MIT License",
        "LSApplicationCategoryType": "public.app-category.developer-tools",
        "NSRequiresAquaSystemAppearance": False,
    },
    "packages": [],
    "includes": ["tkinter"],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
