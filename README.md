# LoFi HUD

A minimalist, zero-ad background audio daemon for Windows. It operates silently in the system tray, responds to global hotkeys (and native Bluetooth media keys), and summons a hardware-accelerated, primary-display-anchored HUD overlay to display track info and volume over any active window.

## Features
* **Ad-Free Local Playback:** Plays local audio files (.mp3, .wav, .flac, .ogg, .m4a, .aac, .opus, .wma) seamlessly on shuffle & loop via the headless VLC engine.
* **Global & Media Keybinds:** Control playback from any application using custom modifier hotkeys or physical headset/keyboard media buttons.
* **Modern Vector HUD:** Crisp, pixel-perfect vector icons rendered via Pillow with smooth fade transitions, progress bars, and high-DPI scaling.
* **Dynamic System Tray:** Real-time hover tooltips (`LoFi HUD — ▶ Track Name`), 1-click library rescan, and instant music folder access.
* **Settings UI with Live Theme Preview:** Tabbed interface with 6 handcrafted themes (*Harbor Night, Tokyo Night, Rosé Pine, Polar Dusk, Gruvbox Warm, and Catppuccin Latte*), persistent window geometry, and hotkey configuration.
* **Smart Track Title Cleaning:** Automatically strips downloader prefixes, track numbering, bitrates, and video tags for a clean display.
* **Zero-Delay Startup & Search Indexing:** Instant launch on Windows login via Startup shortcut and full Windows Search indexing.
* **Single-Instance Protection:** Win32 named mutex prevents duplicate background processes, automatically focusing Settings if launched again.
* **Bluetooth Auto-Pause:** Automatically pauses playback when a chosen Bluetooth device disconnects.

## Installation & Usage

### Option 1: One-Click Installer (Recommended)
1. Download **`LoFiHUD_Setup_v1.0.0.exe`** from the [Releases](https://github.com/rutamt/lofi-player/releases) page.
2. Run the setup wizard (no Administrator / UAC rights required).
3. The app starts immediately in your system tray and creates Start Menu and autostart shortcuts.
4. Right-click the tray icon and select **Open Music Folder** to drop in your favorite songs.

### Option 2: Portable / Source
1. Clone the repository and install requirements: `pip install -r requirements.txt`.
2. Run `python lofi_hud.py`.

## Default Keybinds
* **Play/Pause:** `Alt + Q` (or hardware media play/pause)
* **Next Track:** `Alt + 2` (or hardware media next)
* **Previous Track:** `Alt + 1` (or hardware media prev)
* **Show Current Song:** `Alt + 3`
* **Ignore / Remove Current Song:** `Alt + 4` (moves file to `Ignored_Lofi`)
* **Volume Up/Down:** `Alt + Up Arrow` / `Alt + Down Arrow`

## Uninstallation
LoFi HUD is designed to uninstall completely cleanly without leaving orphan files or deleting your music:

* **Via Windows Settings:**
  1. Open Windows **Settings** → **Apps** → **Installed apps**.
  2. Find **LoFi HUD**, click `...`, and select **Uninstall**.
* **Via Command Line:**
  ```powershell
  lofi_hud.exe --uninstall
  # or from source:
  python lofi_hud.py --uninstall
  ```

> [!NOTE]
> The uninstaller removes all application files, Start Menu shortcuts, autostart entries, and AppData settings, but **strictly preserves your songs and music folder**.

## Building from Source & Compiling the Installer

### 1. Build the Application Directory
```bash
pip install -r requirements.txt pyinstaller
pyinstaller lofi_hud.spec
```
The compiled application will be generated in `dist/lofi_hud/`.

### 2. (Optional) Bundle Portable VLC
To make the app completely independent of system VLC installs:
1. Download the official 64-bit portable VLC `.zip` from [VideoLAN](https://download.videolan.org/pub/videolan/vlc/).
2. Copy `libvlc.dll`, `libvlccore.dll`, and the `plugins/` directory into `dist/lofi_hud/`.

### 3. Compile the Inno Setup Installer
1. Install [Inno Setup 6](https://jrsoftware.org/isdl.php) (`winget install JRSoftware.InnoSetup`).
2. Right-click `installer.iss` and click **Compile** (or run `iscc installer.iss` in PowerShell).
3. The finished **`LoFiHUD_Setup_v1.0.0.exe`** installer will be output into the `dist/` directory!

