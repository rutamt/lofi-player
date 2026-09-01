# LoFi HUD

A minimalist, zero-ad background audio daemon for Windows. It operates silently in the system tray, responds to global hotkeys (and native Bluetooth media keys), and summons a hardware-accelerated, multi-monitor-aware HUD overlay to display the current track and volume over any active window.

## Features
* **Ad-Free Local Playback:** Plays local audio files seamlessly on loop via the headless VLC engine.
* **Global & Media Keybinds:** Control playback from any application using custom modifier hotkeys or physical headset/keyboard media buttons.
* **Non-Intrusive HUD:** A fully responsive, DPI-aware Tkinter overlay that sizes dynamically to the song title and auto-hides.
* **Modern Settings UI:** CustomTkinter interface with 5 unified themes, editable hotkey interceptors, and customizable HUD positioning.
* **Smart String Cleaning:** Automatically strips out dashes, underscores, and file extensions from downloaded MP3s for a clean display.
* **Auto-Start Integration:** Silently injects itself into the Windows boot registry.

## Installation & Usage
1. Download the latest `lofi_hud.exe` from the Releases page.
2. Place the executable in a dedicated folder (e.g., `C:\Tools\LoFiHUD`).
3. Run the application. It will automatically generate a `Lofi` folder and a `config.json` file in the same directory.
4. Drop your `.mp3`, `.wav`, or `.flac` files into the newly created `Lofi` folder. One good source is [OpenLofi](https://github.com/btahir/open-lofi)
5. Double-click the custom icon in your system tray to open Settings, configure your keybinds, and apply themes.

## Default Keybinds
* **Play/Pause:** `Alt + Q` (or hardware media play/pause)
* **Next Track:** `Alt + 2` (or hardware media next)
* **Previous Track:** `Alt + 1` (or hardware media prev)
* **Show Current Song:** `Alt + 3`
* **Volume Up/Down:** `Alt + Up Arrow` / `Alt + Down Arrow`

## Building from Source

**Prerequisites:**
* Python 3.8+
* 64-bit VLC Media Player installed on the host system.
* An icon file named `icon.ico` placed in the root directory. (An example is included from  GuillenDesign (Paulo Guillen) on [icons.com](https://icon-icons.com/icon/music/21178))

**1. Install Dependencies:**
```bash
pip install python-vlc pynput pystray pillow customtkinter

```

**2. Compile Executable:**
Run the following PyInstaller command to bundle the script and the icon into a single, headless executable:

```bash
pyinstaller --onefile --noconsole --hidden-import "pynput.keyboard._win32" --icon="icon.ico" --add-data "icon.ico;." lofi_hud.py

