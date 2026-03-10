#!/usr/bin/env bash
# ──────────────────────────────────────────────────────
#  create_dmg.sh — Package .app into .dmg for distribution
# ──────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"

APP_PATH="dist/OpenClaw Installer.app"
DMG_NAME="OpenClaw-Installer"
DMG_PATH="dist/${DMG_NAME}.dmg"
VOL_NAME="OpenClaw Installer"

if [ ! -d "$APP_PATH" ]; then
    echo "❌ App not found at: $APP_PATH"
    echo "   Run ./build_app.sh first."
    exit 1
fi

echo "🦞 Creating DMG…"

# Remove old DMG
rm -f "$DMG_PATH"

# Try create-dmg (prettier) first, fall back to hdiutil
if command -v create-dmg &>/dev/null; then
    create-dmg \
        --volname "$VOL_NAME" \
        --volicon "resources/openclaw.icns" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 80 \
        --icon "OpenClaw Installer.app" 175 190 \
        --app-drop-link 425 190 \
        --hide-extension "OpenClaw Installer.app" \
        "$DMG_PATH" \
        "$APP_PATH"
else
    echo "ℹ️  create-dmg not found, using hdiutil…"
    echo "   (Install with: brew install create-dmg for prettier DMG)"

    TMP_DMG=$(mktemp /tmp/openclaw_dmg.XXXXXX).dmg
    MOUNT_DIR=$(mktemp -d /tmp/openclaw_mount.XXXXXX)

    # Create writable DMG
    hdiutil create -size 200m -fs HFS+ -volname "$VOL_NAME" "$TMP_DMG"
    hdiutil attach "$TMP_DMG" -mountpoint "$MOUNT_DIR"

    # Copy app
    cp -R "$APP_PATH" "$MOUNT_DIR/"

    # Create Applications symlink
    ln -s /Applications "$MOUNT_DIR/Applications"

    # Unmount & convert to read-only compressed DMG
    hdiutil detach "$MOUNT_DIR"
    hdiutil convert "$TMP_DMG" -format UDZO -o "$DMG_PATH"
    rm -f "$TMP_DMG"
fi

echo ""
echo "✅ DMG created: $DMG_PATH"
echo "   Size: $(du -h "$DMG_PATH" | cut -f1)"
