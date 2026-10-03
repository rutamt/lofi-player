# LoFi HUD

A minimalist, zero-ad background audio daemon for Windows. 

LoFi HUD operates silently in the system tray, responds to global hotkeys (and native Bluetooth media keys), and summons a hardware-accelerated, primary-display-anchored HUD overlay to display track info and volume over any active window without taking focus.

---

## ✨ Features
* **Zero-Ad Local Playback:** Plays local audio files seamlessly on shuffle and loop with low CPU and RAM usage.
* **Modern Vector HUD:** Crisp vector icons with smooth fade transitions, progress bars, and high-DPI scaling.
* **Global & Media Keybinds:** Control playback using custom keybinds that can be accessed anywhere.
* **Dynamic System Tray:** Real-time hover tooltips (`LoFi HUD — ▶ Track Name`), 1-click library rescan, and instant music folder access.
* **Smart Track Title Cleaning:** Automatically strips downloader prefixes, track numbering, bitrates, and video tags for a clean display.
* **Auto Startup & Windows Search:** Automatically starts up after Windows restarts.
* **Bluetooth Auto-Pause:** Automatically pauses playback when your selected Bluetooth device disconnects.

---

## 🚀 How to Install

### Option 1: One-Click Installer (Recommended)
1. Download **`LoFiHUD_Setup_v1.0.0.exe`** from the [Releases](https://github.com/rutamt/lofi-player/releases) page.
2. Run the installer wizard. No Administrator / UAC rights are required, and neither Python nor VLC needs to be pre-installed—everything is fully self-contained!
3. The app will launch directly into your system tray and will automatically appear in Windows Search.

### Option 2: Running from Source
1. Clone the repository:
   ```bash
   git clone https://github.com/rutamt/lofi-player.git
   cd lofi-player
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python lofi_hud.py
   ```

### 🗑 Uninstallation
LoFi HUD is designed to uninstall completely cleanly:
* **Via Windows Settings:** Go to **Settings** → **Apps** → **Installed apps**, search for **LoFi HUD**, and click **Uninstall**.
* **Via Command Line:** Run `lofi_hud.exe --uninstall` (or `python lofi_hud.py --uninstall`).

> [!NOTE]
> The uninstaller removes all application files, Start Menu shortcuts, autostart entries, and AppData settings. By default, **your music folder and songs are safely preserved**, but you can optionally choose to delete the music folder as well when prompted.

---

## 🎵 How to Add Music

1. **Open Your Music Folder:**
   - Right-click the LoFi HUD system tray icon and select **Open Music Folder**.
   - *(Or open Settings by double-clicking the tray icon and click the **Open Folder** button).*
2. **Drop Your Audio Files In:**
   - Supported formats: `.mp3`, `.flac`, `.wav`, `.m4a`, `.ogg`, `.aac`, `.opus`, and `.wma`.
   - LoFi HUD automatically loops, shuffles, and cleans up track titles. If the library was empty, adding files and pressing Play will automatically rescan without needing a restart!

### 🎧 Need Free LoFi Music?
Check out **[OpenLofi](https://github.com/btahir/open-lofi)** by Bashar Tahir. It's a fantastic collection of high-quality, copyright-free, royalty-free LoFi tracks that you can download and drop into your LoFi music folder. Just make sure to only put the audio files, no JSONs.

---

## ⌨ Default Keybinds

| Action | Shortcut |
|---|---|
| **Play / Pause** | `Alt + Q` (or hardware media play/pause) |
| **Next Track** | `Alt + 2` (or hardware media next) |
| **Previous Track** | `Alt + 1` (or hardware media previous) |
| **Show Current Song HUD** | `Alt + 3` |
| **Ignore / Remove Current Song** | `Alt + 4` (safely moves file to `Ignored_Lofi`) |
| **Volume Up / Down** | `Alt + Up Arrow` / `Alt + Down Arrow` |

*Note: All keybinds and the modifier key (`Alt`, `Ctrl`, or `Shift`) can be fully customized in the Settings window.*

---

## 🎨 Themes
LoFi HUD includes 6 carefully curated, eye-pleasing themes designed for long focus sessions:
* **Harbor Night** (Deep oceanic navy with vibrant cyan)
* **Tokyo Night** (Neon indigo with soft sky blue)
* **Rosé Pine** (Muted rose gold with warm pine undertones)
* **Polar Dusk** (Nordic frosted ice with polar blue)
* **Gruvbox Warm** (Cozy retro groove with amber accent)
* **Catppuccin Latte** (Crisp light mode with soothing lavender)

---

## 👏 Credits & Acknowledgments
* **Created by:** Rutam and Gemini
* **Music Library Recommendation:** [OpenLofi](https://github.com/btahir/open-lofi) by [Bashar Tahir](https://github.com/btahir)
* **Icon Design:** Paulo Guillen (GuillenDesign) on [icon-icons.com](https://icon-icons.com/icon/music/21178)
* **Core Libraries:**
  * [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) by Tom Schimansky (UI framework)
  * [libvlc](https://www.videolan.org/vlc/libvlc.html) by the VideoLAN Team (Audio engine)
  * [pynput](https://github.com/moses-palmer/pynput) (Global input hooks)
  * [pystray](https://github.com/moses-palmer/pystray) (System tray integration)
  * [Pillow](https://python-pillow.org/) (Vector graphic rendering)
