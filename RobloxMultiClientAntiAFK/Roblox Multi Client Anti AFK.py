import sys
import os
import time
import threading
from datetime import datetime
import configparser
import ctypes
import ctypes.wintypes
import traceback
import json

try:
    import psutil
    import win32gui
    import win32con
    import win32process
    import pynput
    import pyautogui
    import pydirectinput
    import customtkinter as ctk
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    ctypes.windll.user32.MessageBoxW(0, 
        "Missing libraries!\nPlease run: pip install psutil pywin32 pynput pyautogui pydirectinput customtkinter", 
        "Error", 0)
    sys.exit(1)

def hide_console():
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd != 0:
        ctypes.windll.user32.ShowWindow(hwnd, win32con.SW_HIDE)

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.001

CONFIG_FILE = "config.ini"
NOTES_FILE = "notes_temp.json"

def relaunch_as_admin():
    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            return
    except:
        pass

    params = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    sys.exit(1)

DEFAULT_CONFIG = {
    'Main Settings': {
        'loop_interval_seconds': '1080',
        'stop_hotkey': 'f12'
    },
    'Other Settings': {
        'window_stay_duration': '0',
        'target_process_name': 'RobloxPlayerBeta.exe',
        'blacklist_minimize': 'RobloxPlayerBeta.exe',
        'restore_original_window': 'True',
        'key_press_1': 'o',
        'key_hold_duration_1': '0.1',
        'key_press_2': 'i',
        'key_hold_duration_2': '0',
        'click_before_key': 'True',
        'window_switch_delay': '0.02',
        'post_action_delay': '0.05',
        'mouse_movement_duration': '0.0',
        'pre_action_delay': '0.01',
        'block_input': 'True',
        'note_box_width': '240',
        'overlay_color': '#FF0000',
        'overlay_thickness': '5',
        'overlay_fade_speed': '2.0',
        'overlay_opacity': '0.8'
    }
}

class ConfigManager:
    MAIN_KEYS = ['loop_interval_seconds', 'stop_hotkey']

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.load()

    def load(self):
        self.config.clear()
        if not os.path.exists(CONFIG_FILE):
            self.config.read_dict(DEFAULT_CONFIG)
            self.save()
        else:
            self.config.read(CONFIG_FILE)
            
            if self.config.has_section('Settings'):
                for k, v in self.config.items('Settings'):
                    self.set(k, v)
                self.config.remove_section('Settings')
                self.save()

            self.migrate_keys()
            self.save()

            for section, keys in DEFAULT_CONFIG.items():
                if not self.config.has_section(section):
                    self.config.add_section(section)
                for key, val in keys.items():
                    if self.config.get(section, key, fallback=None) is None:
                        self.config.set(section, key, val)
            self.save()

    def migrate_keys(self):
        key_map = {
            'interval_seconds': 'loop_interval_seconds',
            'switch_delay': 'window_switch_delay',
            'mouse_move_duration': 'mouse_movement_duration',
            'hold_duration_1': 'key_hold_duration_1',
            'hold_duration_2': 'key_hold_duration_2',
            'hold_key_1': 'key_press_1',
            'hold_key_2': 'key_press_2',
            'stay_seconds': 'window_stay_duration',
            'pre_action_delay': 'pre_action_delay',
            'post_minimize_delay': 'post_action_delay',
            'process_name': 'target_process_name'
        }
        
        for old_key, new_key in key_map.items():
            val = self.get(old_key)
            if val is not None:
                self.set(new_key, val)
                self.remove_key(old_key)

    def remove_key(self, key):
        for section in self.config.sections():
            if self.config.has_option(section, key):
                self.config.remove_option(section, key)

    def save(self):
        with open(CONFIG_FILE, 'w') as configfile:
            content = ""
            sections = self.config.sections()
            for i, section in enumerate(sections):
                content += f"[{section}]\n"
                for key, val in self.config.items(section):
                    content += f"{key} = {val}\n"
                if i < len(sections) - 1:
                    content += "\n"
            configfile.write(content)

    def get(self, key, fallback=None):
        for section in self.config.sections():
            val = self.config.get(section, key, fallback=None)
            if val is not None:
                return val
        return fallback

    def set(self, key, value):
        sec = 'Main Settings' if key in self.MAIN_KEYS else 'Other Settings'
        if not self.config.has_section(sec):
            self.config.add_section(sec)
        self.config.set(sec, key, str(value))
        self.save()

class RobloxManager:
    def __init__(self, config_mgr):
        self.config_mgr = config_mgr
        self.windows = []
        self.refresh_windows()

    def refresh_windows(self):
        self.windows = []
        process_name = self.config_mgr.get('target_process_name', 'RobloxPlayerBeta.exe')
        target_pids = set()
        try:
            for p in psutil.process_iter(['pid', 'name', 'create_time']):
                if p.info['name'] == process_name:
                    target_pids.add(p.info['pid'])
        except Exception:
            return

        hwnd_map = {}
        def callback(hwnd, extra):
            try:
                if win32gui.IsWindowVisible(hwnd):
                    _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                    if found_pid in target_pids:
                        if found_pid not in hwnd_map:
                            hwnd_map[found_pid] = []
                        hwnd_map[found_pid].append(hwnd)
            except Exception:
                pass
        
        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass

        for p in psutil.process_iter(['pid', 'create_time']):
            if p.info['pid'] in hwnd_map:
                for hwnd in hwnd_map[p.info['pid']]:
                    self.windows.append({
                        'pid': p.info['pid'],
                        'hwnd': hwnd,
                        'title': win32gui.GetWindowText(hwnd),
                        'start_time': p.info['create_time']
                    })
        
        self.windows.sort(key=lambda x: x['start_time'])

    def force_foreground_window(self, hwnd):
        try:
            if not win32gui.IsWindow(hwnd):
                return False
            
            if win32gui.GetForegroundWindow() == hwnd:
                return True

            shell = pynput.keyboard.Controller()
            shell.press(pynput.keyboard.Key.alt)
            shell.release(pynput.keyboard.Key.alt)

            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 0, 0, 0, 0, 
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception:
            return False

class RobloxSwitcherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Roblox Multi Client Anti AFK")
        self.root.wm_attributes('-topmost', True)
        
        self.config_mgr = ConfigManager()
        self.notes_data = {}
        self.load_notes()
        
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.roblox_mgr = RobloxManager(self.config_mgr)
        
        self.is_running = False
        self.is_switching = False
        self.stop_event = threading.Event()
        self.hotkey_listener = None
        self.last_switch_time = time.time()
        self.instance_vars = {}
        self.instance_time_vars = {}
        self.instance_pid_vars = {}
        self.window_start_times = {}
        self.note_widgets_list = []
        self.alt_pressed = False
        self.startup_pids = set()
        self.log_history = []

        self.log_window = None
        self.log_window_text = None

        self.current_overlay_hwnd = None
        self.active_alpha = 0.0
        self.target_alpha = 0.0
        self.ghost_alpha = 0.0
        self.active_anim_job = None
        self.ghost_anim_job = None

        self.root.bind("<Button-1>", self.on_global_click)
        self.root.bind("<FocusOut>", self.on_focus_out)

        self.setup_overlay()
        self.setup_ui()
        self.refresh_list()
        self.setup_hotkey()
        self.check_admin()
        self.log("Application started.")
        self.center_window()
        self.root.after(1000, lambda: self.root.wm_attributes('-topmost', False))

    def load_notes(self):
        try:
            if os.path.exists(NOTES_FILE):
                with open(NOTES_FILE, 'r', encoding='utf-8') as f:
                    self.notes_data = json.load(f)
            else:
                self.notes_data = {}
        except Exception:
            self.notes_data = {}

    def save_notes(self):
        try:
            with open(NOTES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.notes_data, f, indent=2)
        except Exception:
            pass

    def update_note(self, pid, text_var):
        try:
            text = text_var.get()
            str_pid = str(pid)
            if text:
                self.notes_data[str_pid] = text
            elif str_pid in self.notes_data:
                del self.notes_data[str_pid]
            self.save_notes()
        except Exception:
            pass

    def on_focus_out(self, event):
        self.hide_overlay()

    def on_global_click(self, event):
        w = event.widget
        if isinstance(w, (ctk.CTkFrame, tk.Frame, ctk.CTkScrollableFrame)):
            self.root.focus()
        self.hide_overlay()

    def center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        
        min_w = 600
        if w < min_w:
            w = min_w
            
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - w) // 2
        y = (screen_h - h) // 2
        
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.resizable(False, False)

    def check_admin(self):
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        if is_admin:
            self.log("Administrator privileges detected.")
        else:
            self.log("Running as Standard User.")

    def setup_overlay(self):
        color = self.config_mgr.get('overlay_color', '#FF0000')
        thickness = int(self.config_mgr.get('overlay_thickness', 5))
        
        self.overlay_active = tk.Toplevel(self.root)
        self.overlay_active.overrideredirect(True)
        self.overlay_active.attributes("-topmost", True)
        self.overlay_active.attributes("-transparentcolor", "black")
        self.overlay_active.config(bg="black")
        self.overlay_active_frame = tk.Frame(self.overlay_active, bg="black", highlightbackground=color, highlightthickness=thickness)
        self.overlay_active_frame.pack(fill="both", expand=True)
        self.overlay_active.withdraw()

        self.overlay_ghost = tk.Toplevel(self.root)
        self.overlay_ghost.overrideredirect(True)
        self.overlay_ghost.attributes("-topmost", True)
        self.overlay_ghost.attributes("-transparentcolor", "black")
        self.overlay_ghost.config(bg="black")
        self.overlay_ghost_frame = tk.Frame(self.overlay_ghost, bg="black", highlightbackground=color, highlightthickness=thickness)
        self.overlay_ghost_frame.pack(fill="both", expand=True)
        self.overlay_ghost.withdraw()

    def _get_geometry(self, hwnd):
        try:
            rect = win32gui.GetWindowRect(hwnd)
            x, y, r, b = rect
            w = r - x
            h = b - y
            
            thickness = int(self.config_mgr.get('overlay_thickness', 5))
            
            x += thickness
            y += thickness
            w -= (thickness * 2)
            h -= (thickness * 2)

            if w > 0 and h > 0 and x > -10000:
                return f"{w}x{h}+{x}+{y}"
        except:
            pass
        return None

    def _animate_active_fade(self):
        try:
            speed_factor = float(self.config_mgr.get('overlay_fade_speed', 2.0))
            if speed_factor < 0.1: speed_factor = 0.1
            
            delay_ms = max(1, int(20 / speed_factor))
            step = 0.05

            if abs(self.active_alpha - self.target_alpha) < 0.05:
                self.active_alpha = self.target_alpha
                self.overlay_active.attributes("-alpha", self.active_alpha)
                self.active_anim_job = None
                return

            if self.active_alpha < self.target_alpha:
                self.active_alpha += step
                if self.active_alpha > self.target_alpha: self.active_alpha = self.target_alpha
            else:
                self.active_alpha -= step
                if self.active_alpha < self.target_alpha: self.active_alpha = self.target_alpha
            
            self.overlay_active.attributes("-alpha", self.active_alpha)
            self.active_anim_job = self.root.after(delay_ms, self._animate_active_fade)
        except Exception:
            self.active_anim_job = None

    def _animate_ghost_fade(self):
        try:
            speed_factor = float(self.config_mgr.get('overlay_fade_speed', 2.0))
            if speed_factor < 0.1: speed_factor = 0.1
            
            delay_ms = max(1, int(20 / speed_factor))
            step = 0.05

            if self.ghost_alpha < 0.05:
                self.ghost_alpha = 0.0
                self.overlay_ghost.attributes("-alpha", 0)
                self.overlay_ghost.withdraw()
                self.ghost_anim_job = None
                return

            self.ghost_alpha -= step
            if self.ghost_alpha < 0: self.ghost_alpha = 0
            
            self.overlay_ghost.attributes("-alpha", self.ghost_alpha)
            self.ghost_anim_job = self.root.after(delay_ms, self._animate_ghost_fade)
        except Exception:
            self.ghost_anim_job = None

    def show_overlay(self, hwnd):
        if self.current_overlay_hwnd == hwnd:
            return

        new_geo = self._get_geometry(hwnd)
        if not new_geo: return

        if self.current_overlay_hwnd is not None:
            old_geo = self.overlay_active.geometry()
            current_alpha = self.active_alpha
            
            if current_alpha > 0.05:
                self.overlay_ghost.geometry(old_geo)
                self.overlay_ghost.attributes("-alpha", current_alpha)
                self.overlay_ghost.deiconify()
                self.ghost_alpha = current_alpha
                if self.ghost_anim_job: self.root.after_cancel(self.ghost_anim_job)
                self.ghost_anim_job = self.root.after(0, self._animate_ghost_fade)

        self.current_overlay_hwnd = hwnd
        self.overlay_active.geometry(new_geo)
        self.overlay_active.deiconify()
        
        max_opacity = float(self.config_mgr.get('overlay_opacity', 0.8))
        self.target_alpha = max_opacity
        self.active_alpha = 0.0
        
        if self.active_anim_job: self.root.after_cancel(self.active_anim_job)
        self.active_anim_job = self.root.after(0, self._animate_active_fade)

    def hide_overlay(self):
        if self.current_overlay_hwnd is None and self.ghost_alpha == 0:
            return

        self.current_overlay_hwnd = None
        self.target_alpha = 0.0
        
        if self.active_anim_job: self.root.after_cancel(self.active_anim_job)
        if self.ghost_anim_job: self.root.after_cancel(self.ghost_anim_job)

        if self.active_alpha > 0.05:
            self.active_anim_job = self.root.after(0, self._animate_active_fade)
        else:
            self.overlay_active.withdraw()
            self.active_anim_job = None

        if self.ghost_alpha > 0.05:
            self.ghost_anim_job = self.root.after(0, self._animate_ghost_fade)
        else:
            self.overlay_ghost.withdraw()
            self.ghost_anim_job = None

    def toggle_log_window(self):
        if self.log_window is None or not self.log_window.winfo_exists():
            self.create_log_window()
        else:
            if self.log_window.state() == 'withdrawn':
                self.log_window.deiconify()
                self.log_window.lift()
            else:
                self.log_window.withdraw()

    def create_log_window(self):
        self.log_window = ctk.CTkToplevel(self.root)
        self.log_window.title("Activity Logs")
        self.log_window.geometry("600x500")
        self.log_window.wm_attributes('-topmost', False)
        self.log_window.protocol("WM_DELETE_WINDOW", self.close_log_window)
        
        frame = ctk.CTkFrame(self.log_window)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.log_window_text = ctk.CTkTextbox(frame, fg_color="#121212", text_color="#00ff00", font=ctk.CTkFont(family="Consolas", size=10))
        self.log_window_text.pack(fill="both", expand=True)
        
        for entry in self.log_history:
            self.log_window_text.insert("end", entry)

    def close_log_window(self):
        if self.log_window:
            self.log_window.withdraw()

    def setup_ui(self):
        self.main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=15, pady=5)

        ctk.CTkLabel(self.main_container, text="Roblox Multi Client Anti AFK", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(5, 5))

        control_frame = ctk.CTkFrame(self.main_container)
        control_frame.pack(fill="x", pady=5)
        control_frame.bind("<Enter>", lambda e: self.hide_overlay())
        
        btn_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        self.btn_start = ctk.CTkButton(btn_frame, text="Start Auto-Switcher", font=ctk.CTkFont(weight="bold"), command=self.toggle_switcher, height=35)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.btn_refresh = ctk.CTkButton(btn_frame, text="Refresh List", fg_color="#4A4D50", hover_color="#3A3D40", font=ctk.CTkFont(weight="bold"), command=self.refresh_list, height=35)
        self.btn_refresh.pack(side="left", fill="x", expand=True, padx=5)

        self.btn_view_log = ctk.CTkButton(btn_frame, text="View Log", fg_color="#607d8b", hover_color="#455a64", font=ctk.CTkFont(weight="bold"), command=self.toggle_log_window, height=35)
        self.btn_view_log.pack(side="right", fill="x", expand=True, padx=(5, 0))

        timer_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        timer_frame.pack(fill="x", pady=2, padx=5)
        timer_frame.bind("<Enter>", lambda e: self.hide_overlay())
        
        ctk.CTkLabel(timer_frame, text="Next Queue In:", font=ctk.CTkFont(size=13)).pack(side="left")
        self.lbl_timer = ctk.CTkLabel(timer_frame, text="--:--", text_color="#00adb5", font=ctk.CTkFont(family="Consolas", size=16, weight="bold"))
        self.lbl_timer.pack(side="left", padx=10)
        self.lbl_status = ctk.CTkLabel(timer_frame, text="Status: Idle", text_color="#ff6b6b", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_status.pack(side="right")

        instances_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        instances_container.pack(fill="both", expand=True, pady=5)

        list_header = ctk.CTkFrame(instances_container, fg_color="transparent")
        list_header.pack(fill="x", padx=5, pady=(5, 0))
        list_header.bind("<Enter>", lambda e: self.hide_overlay())
        ctk.CTkLabel(list_header, text="Active Instances", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left")

        self.scroll_list = ctk.CTkScrollableFrame(instances_container, fg_color="#1E1E1E")
        self.scroll_list.pack(fill="both", expand=True, padx=5, pady=5)

        settings_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        settings_frame.pack(fill="both", expand=True, pady=5)
        settings_frame.bind("<Enter>", lambda e: self.hide_overlay())
        
        settings_frame.columnconfigure(0, weight=1)
        settings_frame.columnconfigure(1, weight=1)
        settings_frame.columnconfigure(2, weight=1)
        settings_frame.columnconfigure(3, weight=1)
        
        ctk.CTkLabel(settings_frame, text="Configuration Settings", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00adb5").grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(settings_frame, text="Loop Interval (Min:Sec):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        interval_input_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        interval_input_frame.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.entry_interval_min = ctk.CTkEntry(interval_input_frame, width=45, height=28)
        self.entry_interval_min.pack(side="left")
        ctk.CTkLabel(interval_input_frame, text=":").pack(side="left", padx=2)
        self.entry_interval_sec = ctk.CTkEntry(interval_input_frame, width=45, height=28)
        self.entry_interval_sec.pack(side="left")

        ctk.CTkLabel(settings_frame, text="Window Switch Delay (s):").grid(row=1, column=2, padx=10, pady=5, sticky="w")
        self.entry_switch_delay = ctk.CTkEntry(settings_frame, width=100, height=28)
        self.entry_switch_delay.grid(row=1, column=3, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(settings_frame, text="Mouse Movement Duration (s):").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_mouse_dur = ctk.CTkEntry(settings_frame, width=100, height=28)
        self.entry_mouse_dur.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(settings_frame, text="Stop Hotkey:").grid(row=2, column=2, padx=10, pady=5, sticky="w")
        self.entry_stop_key = ctk.CTkEntry(settings_frame, width=100, height=28)
        self.entry_stop_key.grid(row=2, column=3, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(settings_frame, text="Key 1 Hold Duration (s):").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.entry_hold_dur_1 = ctk.CTkEntry(settings_frame, width=100, height=28)
        self.entry_hold_dur_1.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(settings_frame, text="Key 2 Hold Duration (s):").grid(row=3, column=2, padx=10, pady=5, sticky="w")
        self.entry_hold_dur_2 = ctk.CTkEntry(settings_frame, width=100, height=28)
        self.entry_hold_dur_2.grid(row=3, column=3, padx=10, pady=5, sticky="w")

        btn_box = ctk.CTkFrame(settings_frame, fg_color="transparent")
        btn_box.grid(row=4, column=0, columnspan=4, pady=(15, 10), sticky="ew")

        self.btn_save = ctk.CTkButton(btn_box, text="Save Settings", command=self.save_settings, height=32)
        self.btn_save.pack(side="left", fill="x", expand=True, padx=(10, 5))

        self.btn_reload = ctk.CTkButton(btn_box, text="Reload Config", command=self.reload_config, height=32, fg_color="#E67E22", hover_color="#D35400")
        self.btn_reload.pack(side="left", fill="x", expand=True, padx=5)

        self.btn_open_folder = ctk.CTkButton(btn_box, text="Open Folder", command=self.open_app_folder, height=32, fg_color="#607d8b", hover_color="#455a64")
        self.btn_open_folder.pack(side="left", fill="x", expand=True, padx=(5, 10))

        self.reload_ui_fields()

    def set_entry_text(self, entry, text):
        entry.delete(0, 'end')
        entry.insert(0, str(text))

    def reload_ui_fields(self):
        total_sec = float(self.config_mgr.get('loop_interval_seconds', '1080'))
        m, s = divmod(int(total_sec), 60)
        s_float = total_sec - (m * 60)
        s_val = int(s_float) if s_float.is_integer() else round(s_float, 2)
        
        self.set_entry_text(self.entry_interval_min, m)
        self.set_entry_text(self.entry_interval_sec, s_val)
        self.set_entry_text(self.entry_stop_key, self.config_mgr.get('stop_hotkey', 'f12'))
        self.set_entry_text(self.entry_switch_delay, self.config_mgr.get('window_switch_delay', '0.02'))
        self.set_entry_text(self.entry_mouse_dur, self.config_mgr.get('mouse_movement_duration', '0.0'))
        self.set_entry_text(self.entry_hold_dur_1, self.config_mgr.get('key_hold_duration_1', '0.1'))
        self.set_entry_text(self.entry_hold_dur_2, self.config_mgr.get('key_hold_duration_2', '0'))

    def reload_config(self):
        self.config_mgr.load()
        self.reload_ui_fields()
        self.setup_hotkey()
        self.refresh_list()
        self.log("Configuration reloaded from file.")

    def log(self, message):
        if "Stopped." in message: return
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_history.append(log_entry)
        
        if self.log_window and self.log_window.winfo_exists() and self.log_window_text:
            self.log_window_text.insert("end", log_entry)
            self.log_window_text.see("end")

    def format_time_ago(self, start_time):
        diff = time.time() - start_time
        d = int(diff // 86400)
        h = int((diff % 86400) // 3600)
        m = int((diff % 3600) // 60)
        
        parts = []
        if d > 0: parts.append(f"{d}d")
        if h > 0: parts.append(f"{h}h")
        if m > 0 or (d == 0 and h == 0): parts.append(f"{m}m")
        
        return " ".join(parts) + " ago"

    def nav_note(self, event, widget, direction):
        if not self.note_widgets_list: return "break"
        try:
            idx = self.note_widgets_list.index(widget)
            next_idx = idx + direction
            if 0 <= next_idx < len(self.note_widgets_list):
                next_widget = self.note_widgets_list[next_idx]
                next_widget.focus_set()
                next_widget.select_range(0, 'end')
                return "break"
        except ValueError:
            pass
        return "break"

    def refresh_list(self):
        self.load_notes()
        
        for widget in self.scroll_list.winfo_children():
            widget.destroy()
            
        self.roblox_mgr.refresh_windows()
        new_vars = {}
        self.instance_time_vars = {}
        self.instance_pid_vars = {}
        self.window_start_times = {}
        self.note_widgets_list = []
        
        current_pids = set(win['pid'] for win in self.roblox_mgr.windows)
        
        to_remove = []
        for pid_str in self.notes_data:
            if int(pid_str) not in current_pids:
                to_remove.append(pid_str)
        
        for pid_str in to_remove:
            del self.notes_data[pid_str]
        
        if to_remove:
            self.save_notes()
        
        try:
            note_box_width = int(self.config_mgr.get('note_box_width', '240'))
        except ValueError:
            note_box_width = 240
        
        if not self.roblox_mgr.windows:
            lbl = ctk.CTkLabel(self.scroll_list, text="No instances found.", text_color="#FFFFFF")
            lbl.pack(anchor="w", pady=5)
        else:
            if not self.startup_pids:
                self.startup_pids = set(win['pid'] for win in self.roblox_mgr.windows)
            
            for win in self.roblox_mgr.windows:
                hwnd = win['hwnd']
                pid = win['pid']
                
                is_old_process = pid in self.startup_pids
                default_state = is_old_process

                if hwnd in self.instance_vars:
                    var = self.instance_vars[hwnd]
                else:
                    var = tk.BooleanVar(value=default_state)
                
                new_vars[hwnd] = var
                
                self.window_start_times[hwnd] = win['start_time']
                
                time_str = self.format_time_ago(win['start_time'])
                pid_str = f"PID: {pid}"
                
                time_var = tk.StringVar(value=time_str)
                pid_var = tk.StringVar(value=pid_str)
                
                self.instance_time_vars[hwnd] = time_var
                self.instance_pid_vars[hwnd] = pid_var
                
                row_frame = ctk.CTkFrame(self.scroll_list, fg_color="transparent")
                row_frame.pack(fill="x", pady=2, padx=5)
                
                cb = ctk.CTkCheckBox(row_frame, text="", variable=var, width=20)
                cb.pack(side="left", padx=(0, 5))
                
                time_entry = ctk.CTkEntry(row_frame, textvariable=time_var, fg_color="transparent", border_width=0, height=24, insertontime=0)
                time_entry.pack(side="left", fill="x", expand=True, padx=5)
                time_entry.bind("<Key>", lambda e: "break")
                
                pid_entry = ctk.CTkEntry(row_frame, textvariable=pid_var, fg_color="transparent", border_width=0, height=24, insertontime=0, width=85)
                pid_entry.pack(side="right", padx=5)
                pid_entry.bind("<Key>", lambda e: "break")
                
                note_var = tk.StringVar(value=self.notes_data.get(str(pid), ""))
                note_entry = ctk.CTkEntry(row_frame, textvariable=note_var, placeholder_text="Note...", width=note_box_width, height=24)
                note_entry.pack(side="right", padx=(0, 5))
                
                note_var.trace_add("write", lambda *args, p=pid, v=note_var: self.update_note(p, v))
                
                self.note_widgets_list.append(note_entry)
                note_entry.bind("<Tab>", lambda e, w=note_entry: self.nav_note(e, w, 1))
                note_entry.bind("<Return>", lambda e, w=note_entry: self.nav_note(e, w, 1))
                note_entry.bind("<Down>", lambda e, w=note_entry: self.nav_note(e, w, 1))
                note_entry.bind("<Up>", lambda e, w=note_entry: self.nav_note(e, w, -1))
                
                pid_entry.bind("<Enter>", lambda e, h=hwnd: self.show_overlay(h))
                pid_entry.bind("<Leave>", lambda e: self.hide_overlay())

        self.instance_vars = new_vars

    def open_app_folder(self):
        path = os.path.dirname(os.path.abspath(__file__))
        os.startfile(path)

    def save_settings(self):
        try:
            m = int(self.entry_interval_min.get().strip() or 0)
            s = float(self.entry_interval_sec.get().strip() or 0)
            total_sec = (m * 60) + s
            
            self.config_mgr.set('loop_interval_seconds', str(total_sec))
            self.config_mgr.set('stop_hotkey', self.entry_stop_key.get().strip().lower())
            self.config_mgr.set('window_switch_delay', self.entry_switch_delay.get().strip())
            self.config_mgr.set('mouse_movement_duration', self.entry_mouse_dur.get().strip())
            self.config_mgr.set('key_hold_duration_1', self.entry_hold_dur_1.get().strip())
            self.config_mgr.set('key_hold_duration_2', self.entry_hold_dur_2.get().strip())
            
            self.log("Settings saved.")
            self.setup_hotkey()
            self.refresh_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def setup_hotkey(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        
        stop_keys_str = self.config_mgr.get('stop_hotkey', 'f12')
        stop_keys = [k.strip().lower() for k in stop_keys_str.split(',') if k.strip()]
        
        def on_press(key):
            try:
                current_key = ""
                if hasattr(key, 'name'):
                    current_key = key.name
                elif hasattr(key, 'char'):
                    current_key = key.char
                
                if current_key in ['alt_l', 'alt_r']:
                    self.alt_pressed = True
                
                if current_key == 'tab' and self.alt_pressed:
                    if self.is_switching:
                        self.stop_event.set()
                        self.root.after(0, self.stop_switcher)
                        self.log("Emergency Stop: Alt+Tab detected.")
                    return

                if current_key in stop_keys:
                    if self.is_running:
                        self.root.after(0, self.stop_switcher)
            except: pass

        def on_release(key):
            try:
                if hasattr(key, 'name') and key.name in ['alt_l', 'alt_r']:
                    self.alt_pressed = False
            except: pass

        self.hotkey_listener = pynput.keyboard.Listener(on_press=on_press, on_release=on_release)
        self.hotkey_listener.start()

    def perform_switch(self):
        if self.is_switching: return
        threading.Thread(target=self._switch_logic, daemon=True).start()

    def _switch_logic(self):
        self.is_switching = True
        orig_hwnd = win32gui.GetForegroundWindow()
        
        mx, my = pyautogui.position()
        if mx == 0 and my == 0:
            pyautogui.moveTo(1, 1)
            time.sleep(0.5)
        
        self.log("Processing instances...")

        try:
            self.roblox_mgr.refresh_windows()
            if not self.roblox_mgr.windows:
                self.log("No windows to process.")
                return

            k1 = self.config_mgr.get('key_press_1')
            t1 = float(self.config_mgr.get('key_hold_duration_1'))
            k2 = self.config_mgr.get('key_press_2')
            t2 = float(self.config_mgr.get('key_hold_duration_2'))
            stay = float(self.config_mgr.get('window_stay_duration'))
            switch_delay = float(self.config_mgr.get('window_switch_delay', '0.02'))
            mouse_dur = float(self.config_mgr.get('mouse_movement_duration', '0.0'))
            pre_delay = float(self.config_mgr.get('pre_action_delay', '0.01'))
            
            for win in self.roblox_mgr.windows:
                if self.stop_event.is_set(): break
                
                hwnd = win['hwnd']
                if hwnd in self.instance_vars and not self.instance_vars[hwnd].get():
                    continue

                if self.roblox_mgr.force_foreground_window(hwnd):
                    time.sleep(switch_delay)
                    
                    orig_mouse_x, orig_mouse_y = pyautogui.position()
                    
                    try:
                        rect = win32gui.GetWindowRect(hwnd)
                        is_mouse_inside = (rect[0] <= orig_mouse_x <= rect[2]) and (rect[1] <= orig_mouse_y <= rect[3])
                        
                        if not is_mouse_inside:
                            center_x = (rect[0] + rect[2]) // 2
                            center_y = (rect[1] + rect[3]) // 2
                            pyautogui.moveTo(center_x, center_y, duration=mouse_dur)
                            time.sleep(pre_delay)

                        if k1:
                            pydirectinput.keyDown(k1)
                            time.sleep(t1)
                            pydirectinput.keyUp(k1)
                        
                        if k2:
                            pydirectinput.keyDown(k2)
                            time.sleep(t2)
                            pydirectinput.keyUp(k2)
                        
                        time.sleep(stay)
                        
                        if not is_mouse_inside:
                            pyautogui.moveTo(orig_mouse_x, orig_mouse_y, duration=mouse_dur)
                            
                    except Exception:
                        pass

        finally:
            if orig_hwnd and win32gui.IsWindow(orig_hwnd):
                restore_config = self.config_mgr.get('restore_original_window', 'True').lower() == 'true'
                if restore_config:
                    self.roblox_mgr.force_foreground_window(orig_hwnd)
            
            self.last_switch_time = time.time()
            self.is_switching = False

    def toggle_switcher(self):
        if self.is_running: self.stop_switcher()
        else: self.start_switcher()

    def start_switcher(self):
        self.is_running = True
        self.stop_event.clear()
        self.btn_start.configure(text="Stop Auto-Switcher", fg_color="#ff6b6b", hover_color="#cc5555")
        self.lbl_status.configure(text="Status: Running", text_color="#00ff00")
        self.last_switch_time = time.time()
        self.update_timer()

    def stop_switcher(self):
        self.is_running = False
        self.stop_event.set()
        self.btn_start.configure(text="Start Auto-Switcher", fg_color=['#3a7ebf', '#1f538d'], hover_color=['#325882', '#14375e'])
        self.lbl_status.configure(text="Status: Idle", text_color="#ff6b6b")
        self.lbl_timer.configure(text="--:--")

    def update_instance_times(self):
        for hwnd, time_var in self.instance_time_vars.items():
            if hwnd in self.window_start_times:
                start_time = self.window_start_times[hwnd]
                time_var.set(self.format_time_ago(start_time))

    def update_timer(self):
        if not self.is_running: return
        if self.is_switching:
            self.lbl_timer.configure(text="WAIT")
        else:
            self.update_instance_times()
            rem = max(0, float(self.config_mgr.get('loop_interval_seconds')) - (time.time() - self.last_switch_time))
            self.lbl_timer.configure(text=f"{int(rem//60):02d}:{int(rem%60):02d}")
            if rem <= 0: self.perform_switch()
        self.root.after(1000, self.update_timer)

    def on_closing(self):
        self.save_notes()
        self.stop_switcher()
        if self.hotkey_listener: self.hotkey_listener.stop()
        if self.log_window:
            self.log_window.destroy()
        self.root.destroy()

if __name__ == "__main__":
    try:
        relaunch_as_admin()
        
        app_root = ctk.CTk()
        app = RobloxSwitcherApp(app_root)
        
        hide_console()
        
        app_root.protocol("WM_DELETE_WINDOW", app.on_closing)
        app_root.mainloop()
    except Exception as e:
        error_msg = f"An error occurred:\n{str(e)}\n\n{traceback.format_exc()}"
        print(error_msg)
        try:
            ctypes.windll.user32.MessageBoxW(0, error_msg, "Startup Error", 0)
        except:
            pass
        sys.exit(1)
