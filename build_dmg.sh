#!/usr/bin/env bash
# ==============================================================================
# LoFi HUD — macOS DMG Builder
# Packages LoFi HUD into a standalone .app bundle and drag-and-drop .dmg
# ==============================================================================

set -e

# Change directory to project root
cd "$(dirname "$0")"

echo "🎵 Starting LoFi HUD macOS build..."

# Verify running on macOS
if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "❌ Error: This script must be run on macOS."
    exit 1
fi

# Detect Python executable
if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
    PYINSTALLER=".venv/bin/pyinstaller"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
    PYINSTALLER="pyinstaller"
else
    echo "❌ Error: Python 3 not found."
    exit 1
fi

# Verify PyInstaller is installed
if ! command -v "$PYINSTALLER" &>/dev/null && [ ! -f "$PYINSTALLER" ]; then
    echo "❌ Error: PyInstaller not found. Install with: pip install pyinstaller"
    exit 1
fi

# Extract version from lofi/__init__.py
VERSION=$($PYTHON -c "import lofi; print(lofi.__version__)" 2>/dev/null || echo "1.0.1")
echo "📦 Detected LoFi HUD version: v${VERSION}"

# Generate icon.icns if missing but icon.ico is present
if [ ! -f "icon.icns" ]; then
    if [ -f "icon.ico" ]; then
        echo "🎨 Converting icon.ico to macOS icon.icns..."
        sips -s format png icon.ico --out icon.png &>/dev/null || true
    fi
    if [ -f "icon.png" ]; then
        mkdir -p icon.iconset
        sips -z 16 16     icon.png --out icon.iconset/icon_16x16.png &>/dev/null || true
        sips -z 32 32     icon.png --out icon.iconset/icon_16x16@2x.png &>/dev/null || true
        sips -z 32 32     icon.png --out icon.iconset/icon_32x32.png &>/dev/null || true
        sips -z 64 64     icon.png --out icon.iconset/icon_32x32@2x.png &>/dev/null || true
        sips -z 128 128   icon.png --out icon.iconset/icon_128x128.png &>/dev/null || true
        sips -z 256 256   icon.png --out icon.iconset/icon_128x128@2x.png &>/dev/null || true
        sips -z 256 256   icon.png --out icon.iconset/icon_256x256.png &>/dev/null || true
        sips -z 512 512   icon.png --out icon.iconset/icon_256x256@2x.png &>/dev/null || true
        sips -z 512 512   icon.png --out icon.iconset/icon_512x512.png &>/dev/null || true
        sips -z 1024 1024 icon.png --out icon.iconset/icon_512x512@2x.png &>/dev/null || true
        iconutil -c icns icon.iconset -o icon.icns &>/dev/null || true
        rm -rf icon.iconset
    fi
fi

# Clean previous build artifacts
echo "🧹 Cleaning previous build output..."
rm -rf build
rm -rf "dist/LoFi HUD.app"
rm -rf dist/dmg_staging
rm -f "dist/LoFiHUD_v${VERSION}.dmg"

# Build .app bundle with PyInstaller
echo "🔨 Compiling macOS application bundle with PyInstaller..."
"$PYINSTALLER" lofi_hud_mac.spec --noconfirm

if [ ! -d "dist/LoFi HUD.app" ]; then
    echo "❌ Build failed: dist/LoFi HUD.app was not created."
    exit 1
fi

# Set up DMG staging folder
echo "📂 Preparing DMG drag-and-drop staging layout..."
mkdir -p dist/dmg_staging
cp -R "dist/LoFi HUD.app" dist/dmg_staging/
ln -s /Applications dist/dmg_staging/Applications

# Build the .dmg disk image
DMG_OUTPUT="dist/LoFiHUD_v${VERSION}.dmg"
echo "💿 Generating DMG disk image: ${DMG_OUTPUT}..."
hdiutil create \
    -volname "LoFi HUD" \
    -srcfolder dist/dmg_staging \
    -ov \
    -format UDZO \
    "${DMG_OUTPUT}"

# Clean staging folder
rm -rf dist/dmg_staging

echo "===================================================="
echo "✅ LoFi HUD macOS build completed successfully!"
echo "📍 Installer: ${DMG_OUTPUT}"
echo "===================================================="
