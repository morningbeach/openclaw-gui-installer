#!/bin/bash
# ────────────────────────────────────────────────────────
# Build OpenClaw Menu Bar.app  (macOS status-bar companion)
# ────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")"

PYTHON=/opt/homebrew/bin/python3.13

echo "🦞 Building OpenClaw Menu Bar.app …"

# Clean previous builds
rm -rf build dist

# Build with py2app
$PYTHON setup_menubar.py py2app 2>&1

if [ -d "dist/OpenClaw Menu Bar.app" ]; then
    echo ""
    echo "✅ Build complete!"
    echo "   dist/OpenClaw Menu Bar.app"
    echo ""
    echo "To install: drag to /Applications"
    echo "To run:     open 'dist/OpenClaw Menu Bar.app'"
else
    echo "❌ Build failed"
    exit 1
fi
