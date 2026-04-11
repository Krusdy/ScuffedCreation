import sys
import os
import subprocess
import time
import threading
from datetime import datetime
import configparser
import ctypes
import ctypes.wintypes

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
pyautogui.PAUSE = 0.01

CONFIG_FILE = "config.ini"

def relaunch_as_admin():
    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            return
    except:
        pass

    params = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in sys.argv)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    sys.exit()

class ConfigManager:
    MAIN_KEYS = ['interval_seconds', 'stop_hotkey']

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.load()

    def load(self):
        self.config.clear()
        if not os.path.exists(CONFIG_FILE):
            self.config['Main Settings'] = {
                'interval_seconds': '1080',
                'stop_hotkey': 'f12'
            }
            self.config['Other Settings'] = {
                'stay_seconds': '0',
                'process_name': 'RobloxPlayerBeta.exe',
                'blacklist_minimize': 'RobloxPlayerBeta.exe,Discord.exe',
                'restore_original_window': 'True',
                'hold_key_1': 'o',
                'hold_duration_1': '0',
                'hold_key_2': 'i',
                'hold_duration_2': '0',
                'click_before_key': 'True',
                'switch_delay': '0',
                'post_minimize_delay': '0.5',
                'block_input': 'True'
            }
            self.save()
        else:
            self.config.read(CONFIG_FILE)
            
            if self.config.has_section('Settings'):
                for k, v in self.config.items('Settings'):
                    self.set(k, v)
                self.config.remove_section('Settings')
                self.save()

            if not self.config.has_section('Main Settings'):
                self.config.add_section('Main Settings')
            if not self.config.has_section('Other Settings'):
                self.config.add_section('Other Settings')

            defaults = {
                'interval_seconds': '1080',
                'stop_hotkey': 'f12',
                'stay_seconds': '0',
                'process_name': 'RobloxPlayerBeta.exe',
                'blacklist_minimize': 'RobloxPlayerBeta.exe,Discord.exe',
                'restore_original_window': 'True',
                'hold_key_1': 'o',
                'hold_duration_1': '0',
                'hold_key_2': 'i',
                'hold_duration_2': '0',
                'click_before_key': 'True',
                'switch_delay': '0',
                'post_minimize_delay': '0.5',
                'block_input': 'True'
            }
            for key, val in defaults.items():
                if self.get(key) is None:
                    self.set(key, val)

    def save(self):
        with open(CONFIG_FILE, 'w') as configfile:
            for section in self.config.sections():
                configfile.write(f"[{section}]\n")
                for key, val in self.config.items(section):
                    configfile.write(f"{key} = {val}\n")
                configfile.write("\n")

    def get(self, key, fallback=None):
        sec = 'Main Settings' if key in self.MAIN_KEYS else 'Other Settings'
        return self.config.get(sec, key, fallback=fallback)

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
        processes = []
        process_name = self.config_mgr.get('process_name', 'RobloxPlayerBeta.exe')
        try:
            for p in psutil.process_iter(['pid', 'name', 'create_time']):
                if p.info['name'] == process_name:
                    processes.append(p)
        except Exception:
            return

        processes.sort(key=lambda x: x.info['create_time'])

        for p in processes:
            def callback(hwnd, extra):
                try:
                    if win32gui.IsWindowVisible(hwnd):
                        _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                        if found_pid == p.info['pid']:
                            self.windows.append({
                                'pid': p.info['pid'],
                                'hwnd': hwnd,
                                'title': win32gui.GetWindowText(hwnd),
                                'start_time': p.info['create_time']
                            })
                except Exception:
                    pass
            try:
                win32gui.EnumWindows(callback, None)
            except Exception:
                pass

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
        
        self.width = 560
        self.height = 790
        self.center_window()
        
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.config_mgr = ConfigManager()
        self.roblox_mgr = RobloxManager(self.config_mgr)
        
        self.is_running = False
        self.is_switching = False
        self.stop_event = threading.Event()
        self.hotkey_listener = None
        self.last_switch_time = time.time()
        self.instance_vars = {}
        self.alt_pressed = False

        self.setup_overlay()
        self.setup_ui()
        self.refresh_list()
        self.setup_hotkey()
        self.check_admin()
        self.log("Application started.")

    def center_window(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (self.width // 2)
        y = (screen_height // 2) - (self.height // 2)
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.root.resizable(True, True)

    def check_admin(self):
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        if is_admin:
            self.log("Administrator privileges detected.")
        else:
            self.log("Running as Standard User.")

    def setup_overlay(self):
        self.overlay = tk.Toplevel(self.root)
        self.overlay.overrideredirect(True)
        self.overlay.attributes("-topmost", True)
        self.overlay.attributes("-transparentcolor", "black")
        self.overlay.config(bg="black")
        self.overlay_frame = tk.Frame(self.overlay, bg="black", highlightbackground="red", highlightthickness=5)
        self.overlay_frame.pack(fill="both", expand=True)
        self.overlay.withdraw()

    def show_overlay(self, hwnd):
        try:
            rect = win32gui.GetWindowRect(hwnd)
            x, y, r, b = rect
            w = r - x
            h = b - y
            if w > 0 and h > 0 and x > -10000:
                self.overlay.geometry(f"{w}x{h}+{x}+{y}")
                self.overlay.deiconify()
        except:
            pass

    def hide_overlay(self):
        self.overlay.withdraw()

    def open_app_folder(self):
        path = os.path.dirname(os.path.abspath(__file__))
        os.startfile(path)

    def setup_ui(self):
        self.main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=15, pady=5)

        ctk.CTkLabel(self.main_container, text="Roblox Multi Client Anti AFK", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(5, 5))

        control_frame = ctk.CTkFrame(self.main_container)
        control_frame.pack(fill="x", pady=5)
        
        btn_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        self.btn_start = ctk.CTkButton(btn_frame, text="Start Auto-Switcher", font=ctk.CTkFont(weight="bold"), command=self.toggle_switcher, height=35)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.btn_refresh = ctk.CTkButton(btn_frame, text="Refresh List", fg_color="#4A4D50", hover_color="#3A3D40", font=ctk.CTkFont(weight="bold"), command=self.refresh_list, height=35)
        self.btn_refresh.pack(side="right", fill="x", expand=True, padx=(5, 0))

        timer_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        timer_frame.pack(fill="x", pady=2, padx=5)
        
        ctk.CTkLabel(timer_frame, text="Next Queue In:", font=ctk.CTkFont(size=13)).pack(side="left")
        self.lbl_timer = ctk.CTkLabel(timer_frame, text="--:--", text_color="#00adb5", font=ctk.CTkFont(family="Consolas", size=16, weight="bold"))
        self.lbl_timer.pack(side="left", padx=10)
        self.lbl_status = ctk.CTkLabel(timer_frame, text="Status: Idle", text_color="#ff6b6b", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_status.pack(side="right")

        list_frame = ctk.CTkFrame(self.main_container)
        list_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(list_frame, text="Active Instances", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=(5, 0))
        
        self.scroll_list = ctk.CTkScrollableFrame(list_frame, height=120, fg_color="#1E1E1E")
        self.scroll_list.pack(fill="x", padx=10, pady=10)

        log_frame = ctk.CTkFrame(self.main_container)
        log_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(log_frame, text="Activity Log", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=(5, 0))

        self.log_text = ctk.CTkTextbox(log_frame, height=90, fg_color="#121212", text_color="#00ff00", font=ctk.CTkFont(family="Consolas", size=11), state='disabled')
        self.log_text.pack(fill="x", padx=10, pady=10)

        self.settings_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.settings_frame.pack(fill="both", expand=True, pady=5)
        
        ctk.CTkLabel(self.settings_frame, text="Configuration Settings", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00adb5").grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(self.settings_frame, text="Interval (m:s):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        interval_input_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        interval_input_frame.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.entry_interval_min = ctk.CTkEntry(interval_input_frame, width=45, height=28)
        self.entry_interval_min.pack(side="left")
        ctk.CTkLabel(interval_input_frame, text=":").pack(side="left", padx=2)
        self.entry_interval_sec = ctk.CTkEntry(interval_input_frame, width=45, height=28)
        self.entry_interval_sec.pack(side="left")

        ctk.CTkLabel(self.settings_frame, text="Post Min. Delay:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_post_min_delay = ctk.CTkEntry(self.settings_frame, width=300, height=28)
        self.entry_post_min_delay.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(self.settings_frame, text="Stop Hotkey:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.entry_stop_key = ctk.CTkEntry(self.settings_frame, width=300, height=28)
        self.entry_stop_key.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        btn_box = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        btn_box.grid(row=4, column=0, columnspan=2, pady=(15, 10), sticky="w")

        self.btn_save = ctk.CTkButton(btn_box, text="Save Settings", command=self.save_settings, width=140, height=32)
        self.btn_save.pack(side="left", padx=10)

        self.btn_reload = ctk.CTkButton(btn_box, text="Reload Config", command=self.reload_config, width=140, height=32, fg_color="#E67E22", hover_color="#D35400")
        self.btn_reload.pack(side="left", padx=10)

        self.btn_open_folder = ctk.CTkButton(btn_box, text="Open Folder", command=self.open_app_folder, width=140, height=32, fg_color="#607d8b", hover_color="#455a64")
        self.btn_open_folder.pack(side="left", padx=10)

        self.reload_ui_fields()

    def set_entry_text(self, entry, text):
        entry.delete(0, 'end')
        entry.insert(0, str(text))

    def reload_ui_fields(self):
        total_sec = float(self.config_mgr.get('interval_seconds', '1080'))
        m, s = divmod(int(total_sec), 60)
        s_float = total_sec - (m * 60)
        s_val = int(s_float) if s_float.is_integer() else round(s_float, 2)
        
        self.set_entry_text(self.entry_interval_min, m)
        self.set_entry_text(self.entry_interval_sec, s_val)
        self.set_entry_text(self.entry_stop_key, self.config_mgr.get('stop_hotkey', 'f12'))
        self.set_entry_text(self.entry_post_min_delay, self.config_mgr.get('post_minimize_delay', '0.5'))

    def reload_config(self):
        self.config_mgr.load()
        self.reload_ui_fields()
        self.setup_hotkey()
        self.refresh_list()
        self.log("Configuration reloaded from file.")

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        def update_ui():
            self.log_text.configure(state='normal')
            self.log_text.insert("end", f"[{timestamp}] {message}\n")
            self.log_text.see("end")
            self.log_text.configure(state='disabled')
        if threading.current_thread() == threading.main_thread():
            update_ui()
        else:
            self.root.after(0, update_ui)

    def refresh_list(self):
        for widget in self.scroll_list.winfo_children():
            widget.destroy()
            
        self.roblox_mgr.refresh_windows()
        new_vars = {}
        
        if not self.roblox_mgr.windows:
            lbl = ctk.CTkLabel(self.scroll_list, text="No instances found.", text_color="#FFFFFF")
            lbl.pack(anchor="w", pady=5)
        else:
            for win in self.roblox_mgr.windows:
                hwnd = win['hwnd']
                current_state = self.instance_vars.get(hwnd, tk.BooleanVar(value=True))
                if isinstance(current_state, tk.BooleanVar):
                    var = tk.BooleanVar(value=current_state.get())
                else:
                    var = tk.BooleanVar(value=True)
                new_vars[hwnd] = var
                
                time_str = datetime.fromtimestamp(win['start_time']).strftime("%H:%M:%S")
                cb_text = f"[{time_str}] PID: {win['pid']} - {win['title'][:30]}"
                
                cb = ctk.CTkCheckBox(self.scroll_list, text=cb_text, variable=var, font=ctk.CTkFont(family="Consolas", size=11))
                cb.pack(anchor="w", pady=4, padx=5)
                
                cb.bind("<Enter>", lambda e, h=hwnd: self.show_overlay(h))
                cb.bind("<Leave>", lambda e: self.hide_overlay())

        self.instance_vars = new_vars

    def save_settings(self):
        try:
            m = int(self.entry_interval_min.get().strip() or 0)
            s = float(self.entry_interval_sec.get().strip() or 0)
            total_sec = (m * 60) + s
            
            self.config_mgr.set('interval_seconds', str(total_sec))
            self.config_mgr.set('stop_hotkey', self.entry_stop_key.get().strip().lower())
            self.config_mgr.set('post_minimize_delay', self.entry_post_min_delay.get().strip())
            
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
        
        self.log("Processing instances...")

        try:
            self.roblox_mgr.refresh_windows()
            if not self.roblox_mgr.windows:
                self.log("No windows to process.")
                return

            k1 = self.config_mgr.get('hold_key_1')
            t1 = float(self.config_mgr.get('hold_duration_1'))
            k2 = self.config_mgr.get('hold_key_2')
            t2 = float(self.config_mgr.get('hold_duration_2'))
            stay = float(self.config_mgr.get('stay_seconds'))
            switch_delay = float(self.config_mgr.get('switch_delay', '0'))
            
            for win in self.roblox_mgr.windows:
                if self.stop_event.is_set(): break
                
                hwnd = win['hwnd']
                if hwnd in self.instance_vars and not self.instance_vars[hwnd].get():
                    continue

                if self.roblox_mgr.force_foreground_window(hwnd):
                    time.sleep(switch_delay)
                    
                    try:
                        if k1:
                            pydirectinput.keyDown(k1)
                            time.sleep(t1)
                            pydirectinput.keyUp(k1)
                        
                        if k2:
                            pydirectinput.keyDown(k2)
                            time.sleep(t2)
                            pydirectinput.keyUp(k2)
                        
                        time.sleep(stay)
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
        self.log("Stopped.")

    def update_timer(self):
        if not self.is_running: return
        if self.is_switching:
            self.lbl_timer.configure(text="WAIT")
        else:
            rem = max(0, float(self.config_mgr.get('interval_seconds')) - (time.time() - self.last_switch_time))
            self.lbl_timer.configure(text=f"{int(rem//60):02d}:{int(rem%60):02d}")
            if rem <= 0: self.perform_switch()
        self.root.after(1000, self.update_timer)

    def on_closing(self):
        self.stop_switcher()
        if self.hotkey_listener: self.hotkey_listener.stop()
        self.root.destroy()

if __name__ == "__main__":
    relaunch_as_admin()
    hide_console()
    app_root = ctk.CTk()
    app = RobloxSwitcherApp(app_root)
    app_root.protocol("WM_DELETE_WINDOW", app.on_closing)
    app_root.mainloop()
