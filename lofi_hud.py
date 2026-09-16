import os
import sys
import json
import winreg
import threading
import random
import urllib.parse
import urllib.request
import shutil
import re
import time
import ctypes
import PIL.Image
import PIL.ImageDraw
import tkinter as tk
import customtkinter as ctk
import vlc
from pynput import keyboard
import pystray
from pystray import MenuItem as item

# 0. WINDOWS DPI AWARENESS
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

# 1. PATH, THEMES & CONFIGURATION MANAGEMENT
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    bundle_path = sys._MEIPASS 
else:
    application_path = os.path.dirname(os.path.abspath(__file__))
    bundle_path = application_path

CONFIG_FILE = os.path.join(application_path, 'config.json')

THEMES = {
    "Midnight Blue": {"mode": "dark", "bg": "#1e1e2e", "fg": "#4a90e2", "btn_hover": "#357abd"},
    "Nordic Clean": {"mode": "dark", "bg": "#2e3440", "fg": "#88c0d0", "btn_hover": "#81a1c1"},
    "Forest Glow": {"mode": "dark", "bg": "#1c2520", "fg": "#2ecc71", "btn_hover": "#27ae60"},
    "Cherry Blossom": {"mode": "light", "bg": "#fff0f3", "fg": "#ff4d6d", "btn_hover": "#ff758f"},
    "Minimal Light": {"mode": "light", "bg": "#f4f4f5", "fg": "#18181b", "btn_hover": "#3f3f46"},
    "Cyberpunk": {"mode": "dark", "bg": "#09090b", "fg": "#00f0ff", "btn_hover": "#d900ff"}
}

default_config = {
    "music_dir": os.path.join(application_path, 'Lofi'),
    "mod_key": "alt",
    "key_play": "q",
    "key_next": "2",
    "key_prev": "1",
    "key_show_song": "3",
    "key_ignore": "4",
    "key_vol_up": "up",
    "key_vol_down": "down",
    "volume": 50,
    "show_now_playing": True,
    "show_actions": True,
    "hud_position": "Bottom Center",
    "hud_timeout": 2000,
    "hud_song_timeout": 3500,
    "autopause_device": "Disabled",
    "enable_hardware_keys": True,
    "theme": "Midnight Blue"
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                loaded = json.load(f)
                default_config.update(loaded)
        except Exception:
            pass
    if default_config.get("theme") not in THEMES:
        default_config["theme"] = "Midnight Blue"
    return default_config

def save_config():
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

config = load_config()

if not os.path.exists(config["music_dir"]):
    try: os.makedirs(config["music_dir"])
    except: pass

IGNORED_DIR = os.path.join(os.path.dirname(os.path.normpath(config["music_dir"])), 'Ignored_Lofi')

# 2. AUTO-START REGISTRY INJECTION
def enable_autostart():
    if getattr(sys, 'frozen', False):
        exe_path = sys.executable
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "LoFiHUD", 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
        except Exception:
            pass
enable_autostart()

# 3. NATIVE AUDIO DEVICE SCANNER
def get_active_audio_devices():
    devices = []
    render_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, render_path) as key:
            num_subkeys = winreg.QueryInfoKey(key)[0]
            for i in range(num_subkeys):
                try:
                    guid = winreg.EnumKey(key, i)
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{render_path}\\{guid}") as dev_key:
                        state, _ = winreg.QueryValueEx(dev_key, "DeviceState")
                        if state == 1: 
                            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{render_path}\\{guid}\\Properties") as prop_key:
                                name, _ = winreg.QueryValueEx(prop_key, "{b3f8fa53-0004-438e-9003-51a46e139bfc},6")
                                devices.append(name)
                except Exception:
                    continue
    except Exception:
        pass
    return devices

# 4. VLC INITIALIZATION
vlc_paths = [r"C:\Program Files\VideoLAN\VLC", r"C:\Program Files (x86)\VideoLAN\VLC"]
vlc_found_path = None
for path in vlc_paths:
    if os.path.exists(path):
        os.environ['PYTHON_VLC_MODULE_PATH'] = path
        os.environ['PYTHON_VLC_LIB_PATH'] = os.path.join(path, "libvlc.dll")
        os.environ['PATH'] = path + os.pathsep + os.environ.get('PATH', '')
        vlc_found_path = path
        break

plugin_path = os.path.join(vlc_found_path, "plugins")
instance = vlc.Instance('--no-video', f'--plugin-path={plugin_path}')
list_player = instance.media_list_player_new()
media_player = list_player.get_media_player()
media_player.audio_set_volume(config["volume"])

song_paths = []
def load_media():
    global song_paths
    list_player.stop()
    media_list = instance.instance().media_list_new() if hasattr(instance, "instance") else instance.media_list_new()
    song_paths = []
    valid_extensions = ('.mp3', '.wav', '.flac', '.ogg', '.m4a')
    
    if os.path.exists(config["music_dir"]):
        for root_dir, dirs, files in os.walk(config["music_dir"]):
            if 'Ignored_Lofi' in root_dir: continue
            for file in files:
                if file.lower().endswith(valid_extensions):
                    song_paths.append(os.path.join(root_dir, file))
                    
    if song_paths:
        random.shuffle(song_paths)
        for path in song_paths:
            media_list.add_media(instance.media_new(path))
            
    list_player.set_media_list(media_list)
    list_player.set_playback_mode(vlc.PlaybackMode.loop)

load_media()

# 5. FULLY RESPONSIVE GUI & HUD SETUP
ctk.set_appearance_mode(THEMES[config["theme"]]["mode"])

root = ctk.CTk()
root.withdraw()

hud = tk.Toplevel(root)
hud.overrideredirect(True)
hud.attributes('-topmost', True)
hud.attributes('-alpha', 0.0)
hud.withdraw() 

hud_label = tk.Label(hud, text="", font=("Segoe UI", 13, "bold"), padx=25, pady=12)
hud_label.pack(expand=True, fill='both')

hide_timer = None

def hide_hud():
    hud.attributes('-alpha', 0.0)
    hud.withdraw() 

def trigger_hud_internal(message, duration_override=None):
    global hide_timer
    theme_data = THEMES[config["theme"]]
    hud.config(bg=theme_data["bg"])
    hud_label.config(bg=theme_data["bg"], fg=theme_data["fg"], text=message)
    
    hud.deiconify()
    hud.update_idletasks() 
    
    w = hud.winfo_reqwidth()
    h = hud.winfo_reqheight()
    
    user32 = ctypes.windll.user32
    sw = user32.GetSystemMetrics(0)
    sh = user32.GetSystemMetrics(1)
    
    pad_x, pad_y = 30, 50
    pos = config.get("hud_position", "Bottom Center")
    
    if pos == "Top Left": x, y = pad_x, pad_y
    elif pos == "Top Center": x, y = (sw - w) // 2, pad_y
    elif pos == "Top Right": x, y = sw - w - pad_x, pad_y
    elif pos == "Bottom Left": x, y = pad_x, sh - h - pad_y - 40
    elif pos == "Bottom Right": x, y = sw - w - pad_x, sh - h - pad_y - 40
    elif pos == "Center": x, y = (sw - w) // 2, (sh - h) // 2
    else: x, y = (sw - w) // 2, sh - h - 130 

    hud.geometry(f"{w}x{h}+{x}+{y}")
    hud.attributes('-alpha', 0.95)
    
    if hide_timer is not None:
        root.after_cancel(hide_timer)
    
    timeout = duration_override if duration_override else config.get("hud_timeout", 2000)
    hide_timer = root.after(timeout, hide_hud)

def safe_trigger_hud(message, duration_override=None):
    root.after(0, trigger_hud_internal, message, duration_override)

# 6. SMART SONG NAME TRACKER
def get_clean_song_name():
    media = media_player.get_media()
    if not media: return None
    mrl = media.get_mrl()
    if not mrl: return None
    
    parsed_url = urllib.parse.urlparse(mrl)
    clean_path = urllib.request.url2pathname(parsed_url.path)
    filename = os.path.basename(clean_path)
    display_name = os.path.splitext(filename)[0]
    display_name = re.sub(r'[-_]', ' ', display_name)
    return re.sub(r'\s+', ' ', display_name).strip().title()

def get_current_local_path():
    media = media_player.get_media()
    if not media: return None
    mrl = media.get_mrl()
    if not mrl: return None
    parsed_url = urllib.parse.urlparse(mrl)
    return urllib.request.url2pathname(parsed_url.path)

last_played_mrl = None
def track_monitor():
    global last_played_mrl
    if list_player.get_state() == vlc.State.Playing and config["show_now_playing"]:
        media = media_player.get_media()
        if media:
            mrl = media.get_mrl()
            if mrl != last_played_mrl:
                last_played_mrl = mrl
                song_name = get_clean_song_name()
                if song_name:
                    safe_trigger_hud(f"🎵 Now Playing: {song_name}", config.get("hud_song_timeout", 3500))
    root.after(1000, track_monitor)

root.after(1000, track_monitor)

# 7. BLUETOOTH / DEVICE DISCONNECT TRACKER
was_device_present = False
def device_monitor():
    global was_device_present, is_playing
    target = config.get("autopause_device", "Disabled")
    
    if target != "Disabled" and is_playing:
        active_names = get_active_audio_devices()
        
        if target in active_names:
            was_device_present = True
        elif was_device_present:
            force_pause()
            safe_trigger_hud("⏸ Auto-Paused (Device Disconnected)", 5000)
            was_device_present = False
            
    root.after(2000, device_monitor)

root.after(2000, device_monitor)

# 8. AUDIO CONTROLS
is_playing = False

def force_play():
    global is_playing
    if not song_paths: return
    if not is_playing:
        list_player.play()
        is_playing = True
        if config["show_actions"]: safe_trigger_hud("▶ Resumed")

def force_pause():
    global is_playing
    if is_playing:
        list_player.pause()
        is_playing = False
        if config["show_actions"]: safe_trigger_hud("⏸ Paused")

def toggle_audio():
    global is_playing
    if not song_paths:
        if config["show_actions"]: safe_trigger_hud("Folder Empty: Add MP3s")
        return
    if is_playing: force_pause()
    else: force_play()

def next_track():
    if not song_paths: return
    list_player.next()
    global is_playing
    is_playing = True

def prev_track():
    if not song_paths: return
    list_player.previous()
    global is_playing
    is_playing = True

def show_current_song():
    name = get_clean_song_name()
    if name: safe_trigger_hud(f"🎵 {name}", config.get("hud_song_timeout", 3500))
    else: safe_trigger_hud("No Song Playing")

def ignore_current_song():
    global is_playing
    local_path = get_current_local_path()
    song_name = get_clean_song_name()
    
    if local_path and os.path.exists(local_path):
        try:
            if not os.path.exists(IGNORED_DIR):
                os.makedirs(IGNORED_DIR)
            
            dest_path = os.path.join(IGNORED_DIR, os.path.basename(local_path))
            shutil.move(local_path, dest_path)
            
            if local_path in song_paths:
                song_paths.remove(local_path)
                
            safe_trigger_hud(f"🗑 Removed: {song_name}", config.get("hud_song_timeout", 3500))
            list_player.next()
            is_playing = True
        except Exception:
            safe_trigger_hud("❌ Failed to remove file")

def change_volume(delta):
    config["volume"] = max(0, min(100, config["volume"] + delta))
    media_player.audio_set_volume(config["volume"])
    if config["show_actions"]: safe_trigger_hud(f"🔊 Volume: {config['volume']}%")
    save_config() 

# 9. BULLETPROOF HOTKEY & MEDIA KEY TRACKER
pressed_keys = set()
handled_discrete = set()
is_binding = False 
last_media_press = 0

def check_target_key(event_key, cfg_key):
    """Helper: Checks if the currently struck key perfectly matches the config key"""
    target = config[cfg_key].lower()
    if hasattr(event_key, 'char') and event_key.char and event_key.char.lower() == target: 
        return True
    if hasattr(event_key, 'name') and event_key.name and event_key.name.lower() == target: 
        return True
    return False

def on_press(key):
    global last_media_press
    if is_binding: return 
    pressed_keys.add(key)
    
    vk = getattr(key, 'vk', None)
    current_time = time.time()
    
    is_media_key = (key in (keyboard.Key.media_play_pause, keyboard.Key.media_next, keyboard.Key.media_previous) or vk in (176, 177, 178, 179, 250, 251))
    
    if is_media_key:
        if not config.get("enable_hardware_keys", True):
            return
            
        if current_time - last_media_press < 0.3: return
        last_media_press = current_time
        
        if key == keyboard.Key.media_play_pause or vk == 179: toggle_audio()
        elif vk == 250: force_play()
        elif vk in (251, 178): force_pause()
        elif key == keyboard.Key.media_next or vk == 176:
            if is_playing: next_track()
        elif key == keyboard.Key.media_previous or vk == 177:
            if is_playing: prev_track()
        return
    
    mod = config["mod_key"].lower()
    mod_pressed = False
    if mod == "alt": mod_pressed = any(k in pressed_keys for k in [keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r])
    elif mod == "ctrl": mod_pressed = any(k in pressed_keys for k in [keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r])
    elif mod == "shift": mod_pressed = any(k in pressed_keys for k in [keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r])
    
    if not mod_pressed: return

    # ACTION EXECUTION (Based strictly on the single key that triggered this event)
    if check_target_key(key, "key_vol_up"): 
        if is_playing: change_volume(5)
        return
    elif check_target_key(key, "key_vol_down"): 
        if is_playing: change_volume(-5)
        return
        
    if check_target_key(key, "key_play") and 'play' not in handled_discrete:
        toggle_audio()
        handled_discrete.add('play')
    elif check_target_key(key, "key_prev") and 'prev' not in handled_discrete:
        if is_playing: prev_track()
        handled_discrete.add('prev')
    elif check_target_key(key, "key_next") and 'next' not in handled_discrete:
        if is_playing: next_track()
        handled_discrete.add('next')
    elif check_target_key(key, "key_show_song") and 'show_song' not in handled_discrete:
        if is_playing: show_current_song()
        handled_discrete.add('show_song')
    elif check_target_key(key, "key_ignore") and 'ignore' not in handled_discrete:
        if is_playing: ignore_current_song()
        handled_discrete.add('ignore')

def on_release(key):
    if key in pressed_keys:
        pressed_keys.remove(key)
        
    # Only remove the discrete lock if the target action key is explicitly lifted
    if check_target_key(key, "key_play"): handled_discrete.discard('play')
    elif check_target_key(key, "key_prev"): handled_discrete.discard('prev')
    elif check_target_key(key, "key_next"): handled_discrete.discard('next')
    elif check_target_key(key, "key_show_song"): handled_discrete.discard('show_song')
    elif check_target_key(key, "key_ignore"): handled_discrete.discard('ignore')

listener = keyboard.Listener(on_press=on_press, on_release=on_release)
listener.start()

# 10. MODERN CLEAN SETTINGS UI
settings_window = None

def create_card(parent, title):
    card = ctk.CTkFrame(parent, corner_radius=10)
    card.pack(fill="x", padx=10, pady=(0, 15))
    if title:
        ctk.CTkLabel(card, text=title, font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=15, pady=(15, 5))
    return card

def create_row(parent, label_text):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=15, pady=8)
    ctk.CTkLabel(row, text=label_text, width=150, anchor="w", font=("Segoe UI", 12)).pack(side="left")
    return row

def open_settings_window():
    global settings_window
    if settings_window is not None and settings_window.winfo_exists():
        settings_window.focus()
        return

    accent_color = THEMES[config["theme"]]["fg"]
    hover_color = THEMES[config["theme"]]["btn_hover"]

    settings_window = ctk.CTkToplevel(root)
    settings_window.title("LoFi HUD Settings")
    settings_window.geometry("540x960") 
    
    icon_path = os.path.join(bundle_path, 'icon.ico')
    if os.path.exists(icon_path):
        try:
            settings_window.after(200, lambda: settings_window.iconbitmap(icon_path))
        except Exception:
            pass
    
    scroll = ctk.CTkScrollableFrame(settings_window, fg_color="transparent")
    scroll.pack(fill="both", expand=True, padx=10, pady=10)
    
    ctk.CTkLabel(scroll, text="LoFi Configuration", font=("Segoe UI", 24, "bold")).pack(pady=(5, 20))

    # --- CARD 1: THEME & DISPLAY ---
    card_display = create_card(scroll, "Display & Theme")
    
    row_theme = create_row(card_display, "Active Theme:")
    theme_var = ctk.StringVar(value=config.get("theme", "Midnight Blue"))
    ctk.CTkOptionMenu(row_theme, variable=theme_var, values=list(THEMES.keys()), width=220, fg_color=accent_color, button_color=accent_color, button_hover_color=hover_color).pack(side="right")
    
    row_pos = create_row(card_display, "HUD Position:")
    pos_var = ctk.StringVar(value=config.get("hud_position", "Bottom Center"))
    positions = ["Top Left", "Top Center", "Top Right", "Bottom Left", "Bottom Center", "Bottom Right", "Center"]
    ctk.CTkOptionMenu(row_pos, variable=pos_var, values=positions, width=220, fg_color=accent_color, button_color=accent_color, button_hover_color=hover_color).pack(side="right")

    timeout_map = {1000: "1 Second", 1500: "1.5 Seconds", 2000: "2 Seconds", 3500: "3.5 Seconds", 5000: "5 Seconds"}
    rev_timeout = {v: k for k, v in timeout_map.items()}
    
    row_time = create_row(card_display, "Action HUD Timeout:")
    time_var = ctk.StringVar(value=timeout_map.get(config.get("hud_timeout", 2000), "2 Seconds"))
    ctk.CTkOptionMenu(row_time, variable=time_var, values=list(timeout_map.values()), width=220, fg_color=accent_color, button_color=accent_color, button_hover_color=hover_color).pack(side="right")

    row_song_time = create_row(card_display, "Song Info Timeout:")
    song_time_var = ctk.StringVar(value=timeout_map.get(config.get("hud_song_timeout", 3500), "3.5 Seconds"))
    ctk.CTkOptionMenu(row_song_time, variable=song_time_var, values=list(timeout_map.values()), width=220, fg_color=accent_color, button_color=accent_color, button_hover_color=hover_color).pack(side="right")

    # --- CARD 2: BEHAVIOR & AUDIO ---
    card_behavior = create_card(scroll, "Behavior & Audio Devices")
    now_playing_var = ctk.BooleanVar(value=config["show_now_playing"])
    actions_var = ctk.BooleanVar(value=config["show_actions"])
    
    ctk.CTkSwitch(card_behavior, text="Auto Show 'Now Playing' when Track Changes", variable=now_playing_var, progress_color=accent_color).pack(anchor="w", padx=15, pady=8)
    ctk.CTkSwitch(card_behavior, text="Show Volume & Play/Pause HUD", variable=actions_var, progress_color=accent_color).pack(anchor="w", padx=15, pady=(8, 15))
    
    active_devices = get_active_audio_devices()

    current_target = config.get("autopause_device", "Disabled")
    opts = ["Disabled"] + active_devices
    if current_target not in opts:
        opts.append(current_target)

    row_device = create_row(card_behavior, "Auto-Pause Device:")
    device_var = ctk.StringVar(value=current_target)
    ctk.CTkOptionMenu(row_device, variable=device_var, values=opts, width=220, fg_color=accent_color, button_color=accent_color, button_hover_color=hover_color).pack(side="right")

    # --- CARD 3: MUSIC DIRECTORY ---
    card_dir = create_card(scroll, "Music Source")
    dir_frame = ctk.CTkFrame(card_dir, fg_color="transparent")
    dir_frame.pack(fill="x", padx=15, pady=(5, 15))
    dir_entry = ctk.CTkEntry(dir_frame)
    dir_entry.insert(0, config["music_dir"])
    dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

    def browse():
        from tkinter import filedialog
        path = filedialog.askdirectory()
        if path:
            dir_entry.delete(0, tk.END)
            dir_entry.insert(0, path)
            
    ctk.CTkButton(dir_frame, text="Browse", width=60, fg_color=accent_color, hover_color=hover_color, command=browse).pack(side="right")

    # --- CARD 4: KEYBINDS ---
    card_keys = create_card(scroll, "Keybinds")
    
    hardware_keys_var = ctk.BooleanVar(value=config.get("enable_hardware_keys", True))
    ctk.CTkSwitch(card_keys, text="Enable Hardware Media Keys", variable=hardware_keys_var, progress_color=accent_color).pack(anchor="w", padx=15, pady=(10, 5))

    row_mod = create_row(card_keys, "Hold Modifier:")
    mod_var = ctk.StringVar(value=config["mod_key"].upper())
    ctk.CTkOptionMenu(row_mod, variable=mod_var, values=["ALT", "CTRL", "SHIFT"], width=130, fg_color=accent_color, button_color=accent_color, button_hover_color=hover_color).pack(side="right")

    def add_bind_row(parent, label_text, config_key):
        row = create_row(parent, label_text)
        btn = ctk.CTkButton(row, text=config[config_key].upper(), width=130, fg_color=accent_color, hover_color=hover_color)
        btn.pack(side="right")
        
        def start_capture():
            global is_binding
            if is_binding: return
            is_binding = True
            btn.configure(text="Listening...", fg_color="#e63946", hover_color="#c1121f")
            
            def capture_key(key):
                global is_binding
                try: key_name = key.char if hasattr(key, 'char') and key.char else key.name
                except AttributeError: key_name = str(key).replace("Key.", "")
                    
                key_name = str(key_name).lower()
                config[config_key] = key_name
                
                root.after(0, lambda: btn.configure(text=key_name.upper(), fg_color=accent_color, hover_color=hover_color))
                is_binding = False
                return False 
                
            temp_listener = keyboard.Listener(on_press=capture_key)
            temp_listener.start()
            
        btn.configure(command=start_capture)

    add_bind_row(card_keys, "Play/Pause:", "key_play")
    add_bind_row(card_keys, "Next Track:", "key_next")
    add_bind_row(card_keys, "Previous Track:", "key_prev")
    add_bind_row(card_keys, "Show Song Name:", "key_show_song")
    add_bind_row(card_keys, "Remove/Ignore Song:", "key_ignore")
    add_bind_row(card_keys, "Volume Up:", "key_vol_up")
    add_bind_row(card_keys, "Volume Down:", "key_vol_down")
    
    ctk.CTkFrame(card_keys, height=5, fg_color="transparent").pack()

    # --- SAVE BUTTON ---
    def save_and_apply():
        config["theme"] = theme_var.get()
        config["show_now_playing"] = now_playing_var.get()
        config["show_actions"] = actions_var.get()
        config["hud_position"] = pos_var.get()
        config["hud_timeout"] = rev_timeout.get(time_var.get(), 2000)
        config["hud_song_timeout"] = rev_timeout.get(song_time_var.get(), 3500)
        config["autopause_device"] = device_var.get()
        config["enable_hardware_keys"] = hardware_keys_var.get()
        config["music_dir"] = dir_entry.get()
        config["mod_key"] = mod_var.get().lower()
        save_config()
        
        ctk.set_appearance_mode(THEMES[config["theme"]]["mode"])
        load_media() 
        safe_trigger_hud("Settings Saved!")
        settings_window.destroy()

    ctk.CTkButton(scroll, text="Save & Apply", command=save_and_apply, font=("Segoe UI", 14, "bold"), height=40, fg_color=accent_color, hover_color=hover_color).pack(pady=(15, 30))
    ctk.CTkLabel(scroll, text="Created by Tasga & Gemini", font=("Segoe UI", 11), text_color="gray").pack(side="bottom", pady=5)

def tray_open_settings(icon, item):
    root.after_idle(open_settings_window)

# 11. EMBEDDED SYSTEM TRAY ICON
def get_app_icon():
    icon_path = os.path.join(bundle_path, 'icon.ico')
    if os.path.exists(icon_path):
        try: return PIL.Image.open(icon_path)
        except: pass
            
    image = PIL.Image.new('RGB', (64, 64), color=(255, 255, 255))
    dc = PIL.ImageDraw.Draw(image)
    dc.ellipse((10, 10, 54, 54), fill=(0, 229, 255))
    return image

def on_exit(icon, item):
    listener.stop()
    list_player.stop()
    icon.stop()
    os._exit(0)

menu = pystray.Menu(
    item('Settings (Double-Click)', tray_open_settings, default=True),
    item('Play/Pause', lambda i, j: root.after_idle(toggle_audio)),
    item('Next Track', lambda i, j: root.after_idle(next_track)),
    item('Exit', on_exit)
)

tray_icon = pystray.Icon("LoFi HUD", get_app_icon(), "LoFi Player", menu)
threading.Thread(target=tray_icon.run, daemon=True).start()

# 12. RUN GUI MAIN LOOP
root.mainloop()