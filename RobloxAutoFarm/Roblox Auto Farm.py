# TESTING TESTING TESTING TESTING TESTING TESTING TESTING TESTING TESTING TESTING TESTING TESTING TESTING TESTING TESTING TESTING TESTING

import sys
import os
import ctypes
import time
import threading
from datetime import datetime
import configparser

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

SETTINGS_FILE = "settings.ini"
CONFIG_FILE = "config.ini"

def relaunch_as_admin():
    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            return
    except:
        pass
    if getattr(sys, 'frozen', False):
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1)
    else:
        params = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in sys.argv)
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
    sys.exit()

class SettingsManager:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.load()

    def load(self):
        hotkey_defaults = {
            'mode_hotkey': '', 'profile_hotkey': '', 'macro_hotkey': 'numpad1',
            'drag_toggle_hotkey': 'g', 'drag_save_hotkey': 'h',
            'force_stop_hotkey': 'cmd', 'require_capslock': 'True'
        }
        state_defaults = {'mode': '1', 'p1': '0', 'p2': '0', 'p3': '0', 'p4': '0'}

        if os.path.exists(SETTINGS_FILE):
            self.config.read(SETTINGS_FILE)

        if not self.config.has_section('Settings'):
            self.config.add_section('Settings')
        if not self.config.has_section('Selected'):
            self.config.add_section('Selected')

        for k, v in hotkey_defaults.items():
            if not self.config.has_option('Settings', k):
                self.config.set('Settings', k, v)
                
        for k, v in state_defaults.items():
            if not self.config.has_option('Selected', k):
                self.config.set('Selected', k, v)
        self.save()

    def save(self):
        with open(SETTINGS_FILE, 'w') as configfile:
            self.config.write(configfile)

    def get_setting(self, key, fallback=None):
        return self.config.get('Settings', key, fallback=fallback)

    def set_setting(self, key, value):
        self.config.set('Settings', key, str(value))
        self.save()

    def get_mode(self):
        return int(self.config.get('Selected', 'mode', fallback='1'))

    def get_profile(self, mode):
        return int(self.config.get('Selected', f'p{mode}', fallback='0'))

    def save_state(self, mode, profiles_dict):
        self.config.set('Selected', 'mode', str(mode))
        for m, p in profiles_dict.items():
            self.config.set('Selected', f'p{m}', str(p))
        self.save()

class RobloxManager:
    def __init__(self):
        self.process_name = "RobloxPlayerBeta.exe"

    def is_roblox_active(self):
        fg_hwnd = win32gui.GetForegroundWindow()
        if not fg_hwnd:
            return False
        try:
            _, pid = win32process.GetWindowThreadProcessId(fg_hwnd)
            p = psutil.Process(pid)
            if p.name().lower() == self.process_name.lower():
                return True
        except Exception:
            pass
        return False

class RobloxMacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Roblox Macro Hub")
        self.width = 680
        self.height = 800
        self.center_window()
        
        try:
            self.root.iconbitmap("logo.ico")
        except Exception:
            pass
        
        ctk.set_appearance_mode("Dark")
        
        self.main_color = "#4c00b0"
        self.hover_color = "#6a00f4"
        self.btn_color = "#3a0088"

        self.settings_mgr = SettingsManager()
        self.roblox_mgr = RobloxManager()
        
        self.mode_names = {1: "Spam Farm", 2: "Single Key", 3: "Timing Farm", 4: "Drag Farm"}
        self.load_profiles()
        
        self.active_mode = self.settings_mgr.get_mode()
        if self.active_mode not in self.mode_names: self.active_mode = 1
        
        self.active_profile_idx = {m: self.settings_mgr.get_profile(m) for m in self.profiles.keys()}
        for m in self.active_profile_idx:
            if self.active_profile_idx[m] >= len(self.profiles[m]):
                self.active_profile_idx[m] = 0
                
        self.is_running = False
        self.drag_positions = []
        self.binding_target = None
        self.bind_buttons = {}
        self.macro_thread = None
        
        self.setup_ui()
        self.update_status_ui()
        self.start_listeners()
        self.start_macro_loop()
        self.log("Application started.")

    def load_profiles(self):
        default_ini = """[Mode1]
Blox Fruits (Dragon Talon - Quake - Dragonheart - Skull Guitar) = t,y | 1 | c | 2 | c | v | 3 | x | 4 | x | delay:10
Blox Fruits (Quake) = t,y | 2 | c | v | delay:10
Blox Fruits (Sound) = t | 2 | c | delay:10
Blox Fruits (Dragon West) = t,y | 2 | c | x | z | delay:10
Blox Fruits (Fishing Rod) = z | delay:10000
Anime Final Quest (1, 2, 3) = 1 | 2 | 3 | delay:10
Sailor Piece (Z, X, C, V, F, J) = z | x | c | v | f | j | delay:10

[Mode2]
Spam Z = z | delay:10
Spam X = x | delay:10
Spam C = c | delay:10
Spam V = v | delay:10
Spam F = f | delay:10

[Mode3]
Blox Fruits (Dragon East) = press:t | hold:c:5000 | wait:16000
Blox Fruits (Blizzard) = press:t,y | press:v | wait:32000
Blox Fruits (Dark) = press:t,y | hold:c:3000 | hold:x:3000 | wait:1000 | press:v | wait:9000
Titan Fishing (Z, X, C, V) = press:z,x,c,v | wait:100

[Mode4]
Blox Fruits (Control) = drag:3:1:250"""
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'w') as f:
                f.write(default_ini)

        self.profiles = {1: [], 2: [], 3: [], 4: []}
        parser = configparser.ConfigParser()
        parser.read(CONFIG_FILE)

        for mode_num, section in [(1, 'Mode1'), (2, 'Mode2'), (3, 'Mode3'), (4, 'Mode4')]:
            if parser.has_section(section):
                for name, value in parser.items(section):
                    parts = [p.strip() for p in value.split('|')]
                    prof = {"name": name.title()}
                    try:
                        if mode_num == 1:
                            seq = []
                            delay = 100
                            for p in parts:
                                if p.startswith("delay:"):
                                    delay = int(p.split(":")[1])
                                else:
                                    seq.append({"action": "press", "keys": p.split(",")})
                            prof["sequence"] = seq
                            prof["delay"] = delay
                        elif mode_num == 2:
                            prof["key"] = parts[0]
                            prof["delay"] = int(parts[1].split(":")[1]) if len(parts) > 1 and parts[1].startswith("delay:") else 100
                        elif mode_num == 3:
                            seq = []
                            for p in parts:
                                cmds = p.split(":")
                                if cmds[0] == "press":
                                    seq.append({"action": "press", "keys": cmds[1].split(",")})
                                elif cmds[0] == "hold":
                                    seq.append({"action": "hold", "key": cmds[1], "duration": int(cmds[2])})
                                elif cmds[0] == "wait":
                                    seq.append({"action": "wait", "duration": int(cmds[1])})
                            prof["sequence"] = seq
                        elif mode_num == 4:
                            cmds = parts[0].split(":")
                            if cmds[0] == "drag":
                                prof["dragSteps"] = int(cmds[1])
                                prof["dragStepDelay"] = int(cmds[2])
                                prof["delayBetweenDrags"] = int(cmds[3])
                        self.profiles[mode_num].append(prof)
                    except Exception:
                        pass
                        
        for k in self.profiles:
            if not self.profiles[k]:
                self.profiles[k] = [{"name": "Empty Config"}]

    def center_window(self):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (self.width // 2)
        y = (screen_height // 2) - (self.height // 2)
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.root.resizable(False, False)

    def setup_ui(self):
        self.main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=15, pady=10)

        ctk.CTkLabel(self.main_container, text="Roblox Macro Hub", font=ctk.CTkFont(size=22, weight="bold"), text_color=self.hover_color).pack(pady=(5, 10))

        status_frame = ctk.CTkFrame(self.main_container)
        status_frame.pack(fill="x", pady=5)
        
        self.lbl_status = ctk.CTkLabel(status_frame, text="Status: OFF", text_color="#ff6b6b", font=ctk.CTkFont(size=16, weight="bold"))
        self.lbl_status.pack(pady=10)

        controls_frame = ctk.CTkFrame(self.main_container)
        controls_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(controls_frame, text="Select Mode:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 0))
        self.mode_var = ctk.StringVar()
        self.mode_dropdown = ctk.CTkOptionMenu(
            controls_frame, 
            variable=self.mode_var, 
            values=list(self.mode_names.values()), 
            command=self.gui_change_mode,
            fg_color=self.main_color, 
            button_color=self.btn_color, 
            button_hover_color=self.hover_color,
            dynamic_resizing=False
        )
        self.mode_dropdown.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkLabel(controls_frame, text="Select Profile:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(5, 0))
        
        profile_row = ctk.CTkFrame(controls_frame, fg_color="transparent")
        profile_row.pack(fill="x", padx=10, pady=(5, 10))
        
        self.profile_var = ctk.StringVar()
        self.profile_dropdown = ctk.CTkOptionMenu(
            profile_row, 
            variable=self.profile_var, 
            command=self.gui_change_profile,
            fg_color=self.main_color, 
            button_color=self.btn_color, 
            button_hover_color=self.hover_color,
            dynamic_resizing=False
        )
        self.profile_dropdown.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_refresh = ctk.CTkButton(
            profile_row, 
            text="Refresh Config", 
            width=120,
            fg_color=self.btn_color, 
            hover_color=self.hover_color,
            command=self.refresh_config
        )
        self.btn_refresh.pack(side="right")

        settings_frame = ctk.CTkFrame(self.main_container)
        settings_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(settings_frame, text="Hotkeys Configuration", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=2, pady=5)

        hotkeys = [
            ("Change Mode", 'mode_hotkey'),
            ("Change Profile", 'profile_hotkey'),
            ("Start/Stop Macro", 'macro_hotkey'),
            ("Toggle Drag", 'drag_toggle_hotkey'),
            ("Save Drag Pos", 'drag_save_hotkey'),
            ("Force Stop All", 'force_stop_hotkey')
        ]

        for i, (label_text, config_key) in enumerate(hotkeys):
            ctk.CTkLabel(settings_frame, text=label_text).grid(row=i+1, column=0, padx=10, pady=2, sticky="w")
            btn_text = self.settings_mgr.get_setting(config_key)
            if not btn_text:
                btn_text = "Unbound"
            btn = ctk.CTkButton(settings_frame, text=btn_text, width=150, fg_color=self.main_color, hover_color=self.hover_color, command=lambda k=config_key: self.start_bind(k))
            btn.grid(row=i+1, column=1, padx=10, pady=2, sticky="e")
            self.bind_buttons[config_key] = btn

        self.caps_var = ctk.StringVar(value=self.settings_mgr.get_setting('require_capslock'))
        caps_cb = ctk.CTkCheckBox(settings_frame, text="Require CapsLock for Drag", variable=self.caps_var, onvalue="True", offvalue="False", command=self.toggle_capslock)
        caps_cb.grid(row=len(hotkeys)+1, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        log_frame = ctk.CTkFrame(self.main_container)
        log_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(log_frame, text="Activity Log", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=(5, 0))
        self.log_text = ctk.CTkTextbox(log_frame, height=150, fg_color="#121212", text_color=self.hover_color, font=ctk.CTkFont(family="Consolas", size=11), state='disabled')
        self.log_text.pack(fill="x", padx=10, pady=10)

    def refresh_config(self):
        self.is_running = False
        self.load_profiles()
        
        for m in self.active_profile_idx:
            if self.active_profile_idx[m] >= len(self.profiles[m]):
                self.active_profile_idx[m] = 0
                
        self.update_status_ui()
        self.log("Configuration and Profiles reloaded.")

    def toggle_capslock(self):
        self.settings_mgr.set_setting('require_capslock', self.caps_var.get())

    def start_bind(self, config_key):
        self.binding_target = config_key
        for k, btn in self.bind_buttons.items():
            if k == config_key:
                btn.configure(text="Press any key...")
            else:
                val = self.settings_mgr.get_setting(k)
                btn.configure(text=val if val else "Unbound")

    def update_bind_button(self, config_key, key_str):
        btn = self.bind_buttons.get(config_key)
        if btn:
            btn.configure(text=key_str)
        self.log(f"Bound {config_key} to '{key_str}'")

    def gui_change_mode(self, choice):
        for k, v in self.mode_names.items():
            if v == choice:
                self.active_mode = k
                break
        self.is_running = False
        self.settings_mgr.save_state(self.active_mode, self.active_profile_idx)
        self.log(f"Switched to Mode: {choice}")
        self.update_status_ui()

    def gui_change_profile(self, choice):
        m = self.active_mode
        for i, p in enumerate(self.profiles[m]):
            if p.get("name") == choice:
                self.active_profile_idx[m] = i
                break
        self.settings_mgr.save_state(self.active_mode, self.active_profile_idx)
        self.log(f"Switched to Profile: {choice}")
        self.update_status_ui()

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

    def update_status_ui(self):
        m = self.active_mode
        pidx = self.active_profile_idx[m]
        
        self.mode_var.set(self.mode_names[m])
        
        profile_names = [p.get("name", "Unnamed") for p in self.profiles[m]]
        if not profile_names:
            profile_names = ["No profiles found"]
            
        self.profile_dropdown.configure(values=profile_names)
        self.profile_var.set(profile_names[min(pidx, len(profile_names)-1)])
        
        if self.is_running:
            self.lbl_status.configure(text="Status: ON", text_color="#00ff00")
        else:
            self.lbl_status.configure(text="Status: OFF", text_color="#ff6b6b")

    def force_stop_all(self):
        if self.is_running:
            self.is_running = False
            pydirectinput.mouseUp()
            self.log("All Automation Stopped")
            self.update_status_ui()

    def get_key_name(self, key):
        try:
            if hasattr(key, 'name'):
                return key.name
            elif hasattr(key, 'char') and key.char:
                return key.char.lower()
            elif hasattr(key, 'vk') and key.vk is not None and 96 <= key.vk <= 105:
                return f"numpad{key.vk - 96}"
            else:
                return str(key).replace("'", "").lower()
        except Exception:
            return None

    def start_listeners(self):
        def on_press(key):
            try:
                key_name = self.get_key_name(key)
                if not key_name: return

                if self.binding_target:
                    if key_name == 'esc':
                        self.settings_mgr.set_setting(self.binding_target, "")
                        self.root.after(0, self.update_bind_button, self.binding_target, "Unbound")
                    else:
                        self.settings_mgr.set_setting(self.binding_target, key_name)
                        self.root.after(0, self.update_bind_button, self.binding_target, key_name)
                    self.binding_target = None
                    return

                if key_name in ['ctrl', 'ctrl_l', 'ctrl_r', 'shift', 'shift_l', 'shift_r', 'alt', 'alt_l', 'alt_r', 'alt_gr', 'cmd', 'cmd_l', 'cmd_r']:
                    return

                mode_hk = self.settings_mgr.get_setting('mode_hotkey')
                prof_hk = self.settings_mgr.get_setting('profile_hotkey')
                macr_hk = self.settings_mgr.get_setting('macro_hotkey')
                dtog_hk = self.settings_mgr.get_setting('drag_toggle_hotkey')
                dsav_hk = self.settings_mgr.get_setting('drag_save_hotkey')
                fsto_hk = self.settings_mgr.get_setting('force_stop_hotkey')

                if key_name == fsto_hk and fsto_hk:
                    self.root.after(0, self.force_stop_all)
                    
                elif key_name == dtog_hk and dtog_hk:
                    req_caps = self.settings_mgr.get_setting('require_capslock') == 'True'
                    caps_on = win32gui.GetKeyState(win32con.VK_CAPITAL) in (1, -127)
                    if not req_caps or caps_on:
                        if self.active_mode == 4:
                            self.is_running = not self.is_running
                            self.log(f"Drag Farm: {'On' if self.is_running else 'Off'}")
                            self.root.after(0, self.update_status_ui)
                            
                elif key_name == dsav_hk and dsav_hk:
                    req_caps = self.settings_mgr.get_setting('require_capslock') == 'True'
                    caps_on = win32gui.GetKeyState(win32con.VK_CAPITAL) in (1, -127)
                    if not req_caps or caps_on:
                        x, y = pyautogui.position()
                        if len(self.drag_positions) >= 2:
                            self.drag_positions = []
                            self.log("Drag Positions Cleared")
                        else:
                            self.drag_positions.append((x, y))
                            self.log(f"Saved Drag Pos {len(self.drag_positions)}")
                            
                elif key_name == mode_hk and mode_hk:
                    self.active_mode += 1
                    if self.active_mode > 4:
                        self.active_mode = 1
                    self.is_running = False
                    self.settings_mgr.save_state(self.active_mode, self.active_profile_idx)
                    self.log(f"Switched to: {self.mode_names[self.active_mode]}")
                    self.root.after(0, self.update_status_ui)
                    
                elif key_name == macr_hk and macr_hk:
                    self.is_running = not self.is_running
                    self.log(f"{self.mode_names[self.active_mode]}: {'On' if self.is_running else 'Off'}")
                    self.root.after(0, self.update_status_ui)
                    
                elif key_name == prof_hk and prof_hk:
                    m = self.active_mode
                    self.active_profile_idx[m] += 1
                    if self.active_profile_idx[m] >= len(self.profiles[m]):
                        self.active_profile_idx[m] = 0
                    self.settings_mgr.save_state(self.active_mode, self.active_profile_idx)
                    
                    profile_name = self.profiles[m][self.active_profile_idx[m]].get('name', 'Unnamed')
                    self.log(f"Profile: {profile_name}")
                    self.root.after(0, self.update_status_ui)
            except Exception:
                pass

        self.listener = pynput.keyboard.Listener(on_press=on_press)
        self.listener.start()

    def start_macro_loop(self):
        def loop():
            seq_step = 0
            while True:
                if not self.is_running or not self.roblox_mgr.is_roblox_active():
                    time.sleep(0.05)
                    seq_step = 0
                    continue

                if win32gui.GetAsyncKeyState(win32con.VK_LMENU) or win32gui.GetAsyncKeyState(win32con.VK_RMENU):
                    time.sleep(0.2)
                    continue

                m = self.active_mode
                if not self.profiles[m]:
                    time.sleep(0.05)
                    continue

                p = self.profiles[m][self.active_profile_idx[m]]

                if m == 1:
                    seq = p.get("sequence", [])
                    if seq:
                        if seq_step >= len(seq):
                            seq_step = 0
                        step = seq[seq_step]
                        if step.get("action") == "press":
                            for k in step.get("keys", []):
                                pydirectinput.press(k)
                        time.sleep(p.get("delay", 100) / 1000.0)
                        seq_step += 1

                elif m == 2:
                    pydirectinput.press(p.get("key", ""))
                    time.sleep(p.get("delay", 100) / 1000.0)

                elif m == 3:
                    seq = p.get("sequence", [])
                    if seq:
                        if seq_step >= len(seq):
                            seq_step = 0
                        step = seq[seq_step]
                        action = step.get("action")
                        
                        if action == "press":
                            for k in step.get("keys", []):
                                pydirectinput.press(k)
                        elif action == "hold":
                            key = step.get("key", "")
                            pydirectinput.keyDown(key)
                            time.sleep(step.get("duration", 0) / 1000.0)
                            pydirectinput.keyUp(key)
                        elif action == "wait":
                            time.sleep(step.get("duration", 0) / 1000.0)
                            
                        seq_step += 1

                elif m == 4:
                    if len(self.drag_positions) == 2:
                        x1, y1 = self.drag_positions[0]
                        x2, y2 = self.drag_positions[1]
                        drag_steps = p.get("dragSteps", 3)
                        
                        dx = (x2 - x1) / drag_steps
                        dy = (y2 - y1) / drag_steps
                        
                        pyautogui.moveTo(x1, y1)
                        pydirectinput.mouseDown()
                        
                        for i in range(1, drag_steps + 1):
                            pyautogui.moveTo(x1 + dx * i, y1 + dy * i)
                            time.sleep(p.get("dragStepDelay", 1) / 1000.0)
                            
                        pydirectinput.mouseUp()
                        time.sleep(p.get("delayBetweenDrags", 250) / 1000.0)

                time.sleep(0.02)

        self.macro_thread = threading.Thread(target=loop, daemon=True)
        self.macro_thread.start()

    def on_closing(self):
        self.is_running = False
        if hasattr(self, 'listener'):
            self.listener.stop()
        self.root.destroy()

if __name__ == "__main__":
    relaunch_as_admin()
    hide_console()
    app_root = ctk.CTk()
    app = RobloxMacroApp(app_root)
    app_root.protocol("WM_DELETE_WINDOW", app.on_closing)
    app_root.mainloop()
