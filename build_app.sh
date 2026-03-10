#!/usr/bin/env bash
# ──────────────────────────────────────────────────────
#  build_app.sh — Build OpenClaw Installer.app
# ──────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")"

echo "🦞 Building OpenClaw Installer.app …"

# Clean old build
rm -rf build dist

PYTHON=/opt/homebrew/bin/python3.13
PIP=/opt/homebrew/bin/pip3.13

# Check py2app
if ! $PYTHON -c "import py2app" 2>/dev/null; then
    echo "📦 Installing py2app…"
    $PIP install py2app
fi

# Generate a placeholder icon if missing
if [ ! -f resources/openclaw.icns ]; then
    echo "🎨 Generating placeholder icon…"
    mkdir -p resources
    python3 - << 'ICON_PY'
import subprocess, tempfile, os
# Create a simple 512x512 icon with sips (macOS built-in)
png = os.path.join(tempfile.mkdtemp(), "icon.png")
iconset = os.path.join(tempfile.mkdtemp(), "openclaw.iconset")
os.makedirs(iconset, exist_ok=True)
# Use built-in macOS tool to create a colored square as placeholder
for size in [16, 32, 64, 128, 256, 512]:
    name = f"icon_{size}x{size}.png"
    # Create a tiny PPM and convert
    ppm = os.path.join(iconset, f"{size}.ppm")
    with open(ppm, 'wb') as f:
        f.write(f"P6\n{size} {size}\n255\n".encode())
        for y in range(size):
            for x in range(size):
                f.write(bytes([233, 69, 96]))  # #e94560 lobster red
    subprocess.run(["sips", "-s", "format", "png", ppm, "--out",
                    os.path.join(iconset, name)], capture_output=True)
    os.remove(ppm)
    # Also create @2x variants
    if size <= 256:
        name2x = f"icon_{size}x{size}@2x.png"
        subprocess.run(["sips", "-s", "format", "png",
                        os.path.join(iconset, f"icon_{size*2}x{size*2}.png" if size*2 <= 512 else name),
                        "--out", os.path.join(iconset, name2x)], capture_output=True)
subprocess.run(["iconutil", "-c", "icns", iconset, "-o", "resources/openclaw.icns"])
print("✅ Icon created")
ICON_PY
fi

# Build
$PYTHON setup.py py2app

echo ""
echo "✅ Build complete!"
echo "   App: dist/OpenClaw Installer.app"
echo ""
echo "To test: open 'dist/OpenClaw Installer.app'"
echo "To create DMG: ./create_dmg.sh"
