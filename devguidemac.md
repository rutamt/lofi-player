# LoFi HUD — macOS Developer & Testing Guide

This guide covers how to set up the environment, run the app in development mode, test the hotkey and keybind systems, and compile standalone macOS distribution bundles (`.app` and `.dmg`).

---

## 1. Environment Prerequisites

- **macOS**: macOS 12 Monterey or newer (Apple Silicon & Intel supported).
- **Python**: Python 3.10+ (Recommended: Python 3.12 via Homebrew).
- **VLC**: VLC Media Player 64-bit must be installed in `/Applications/VLC.app` for audio playback.

### Initial Setup

```bash
# Clone and enter directory
cd lofi-player

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install required dependencies
pip install -r requirements.txt
```

---

## 2. macOS Accessibility Permissions

macOS security requires explicit Accessibility access for global keystroke monitoring (via `pynput` / Quartz event taps):

1. Go to **System Settings** > **Privacy & Security** > **Accessibility**.
2. If testing in development mode, ensure **Terminal** (or **iTerm**, **VS Code**, etc.) has a checkmark next to it.
3. If testing the compiled app bundle, add and enable **LoFi HUD.app**.

The app also provides shortcuts in **Settings > Controls > macOS Permissions** to open System Settings directly or request the OS prompt.

---

## 3. Running in Development Mode

To run directly from source without bundling:

```bash
# Ensure virtual environment is active
source .venv/bin/activate

# Launch the app
python lofi_hud.py
```

### Checking Logs & Background Output
- When running `python lofi_hud.py`, stdout/stderr will show real-time diagnostics (song loading, volume changes, hotkey triggers).
- To test single instance behavior, open a second terminal and run `python lofi_hud.py`. The running instance will surface its Settings window and display a HUD toast.

---

## 4. Testing Keybinds and Hotkeys

### A. Testing Keybind Remapping
1. Open the Settings window (double-click the menu bar tray icon or right-click > **Settings**).
2. Go to the **Controls** tab.
3. Under **Keybinds**, click any action button (e.g., **Next Track** or **Play/Pause**).
4. The button changes to red with text **"Press key..."**.
5. Press the new key (e.g., `2`, `n`, `space`, arrow keys, etc.):
   - It should immediately capture the key, update the button label, and not crash.
   - Pressing **Escape** cancels capture without changing the key.
   - Holding modifier keys (like Option or Shift) while pressing a character (e.g., Option+2) correctly registers the base key (`2`) rather than macOS unicode dead-key glyphs (`™`).
6. Click **Save & Apply** at the bottom.

### B. Testing the Modifier Glitch Fix
1. Ensure your **Hold Modifier** is set to **OPTION** (default on Mac).
2. Start music playback.
3. Press **Option + 2** to skip to the next track. The track should skip.
4. Release the Option key.
5. Now press **2** alone (e.g. while typing in another app or in the terminal).
   - **Expected behavior**: The track must **NOT** skip.
   - The app actively queries `Quartz.CGEventSourceFlagsState` for the true hardware modifier flags, purging any stale modifiers from memory so action keys never fire alone.

---

## 5. Building the macOS Application & DMG

The project includes an automated build script (`build_dmg.sh`) that converts the code into a signed `.app` bundle and packages a drag-and-drop installer `.dmg`.

### Build Command

```bash
./build_dmg.sh
```

### Build Pipeline Stages:
1. **Icon Generation**: Automatically converts `icon.ico` / `icon.png` to Apple `icon.icns`.
2. **PyInstaller Compilation**: Uses [`lofi_hud_mac.spec`](file:///Users/rutam/Desktop/projects/lofi-player/lofi_hud_mac.spec) to package Python, CustomTkinter assets, PyObjC/Quartz bindings, and dependencies into `dist/LoFi HUD.app`.
3. **DMG Generation**: Stages `dist/LoFi HUD.app` alongside a symlink to `/Applications` and creates `dist/LoFiHUD_v<version>.dmg`.

### Build Outputs
- Application bundle: `dist/LoFi HUD.app`
- Disk image installer: `dist/LoFiHUD_v1.0.1.dmg`

### Testing the Built App
```bash
open "dist/LoFi HUD.app"
```
Or open the DMG to test the drag-and-drop installer:
```bash
open "dist/LoFiHUD_v1.0.1.dmg"
```

---

## 6. Troubleshooting: "Keeps Asking for Accessibility Permissions"

If macOS keeps stating Accessibility permissions are needed even though the checkbox is ON in System Settings:

### Cause 1: Running directly from the DMG (App Translocation)
- **Problem**: Opening `LoFi HUD.app` directly inside the mounted DMG (or Downloads folder) triggers macOS **App Translocation**. macOS isolates the binary to a randomized read-only path in `/private/var/folders/...`. Permissions granted to this temporary path do not persist.
- **Solution**: Drag `LoFi HUD.app` from the DMG into `/Applications`, unmount/eject the DMG, and launch the app from `/Applications`.

### Cause 2: Rebuilding invalidates the cryptographic signature (Ghost Entry)
- **Problem**: Ad-hoc signed builds generate a new Code Directory Hash (`cdhash`) each compile. macOS `TCC.db` remembers the hash of the *previous* build. System Settings displays "LoFi HUD" with the toggle turned ON, but macOS internally rejects the new binary because its hash does not match the old entry.
- **Solution**:
  1. Open **System Settings > Privacy & Security > Accessibility**.
  2. Select **LoFi HUD** in the list and click the **minus (`-`)** button to delete the stale entry (do not just flip the toggle off and on).
  3. Re-open `/Applications/LoFi HUD.app` and approve the prompt, or click the **plus (`+`)** button and add `/Applications/LoFi HUD.app`.

#### Instant Terminal Fix:
You can also instantly wipe the stale cached permission entry with one command:
```bash
tccutil reset Accessibility com.rutamt.lofihud
```
Then re-open the app from `/Applications` and approve the prompt.

