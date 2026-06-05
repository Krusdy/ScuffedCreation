import customtkinter as ctk
import os
import time
import threading
import pygetwindow as gw
import psutil
import win32process
import win32gui
import win32console
import sys
import ctypes
from ctypes import wintypes
import configparser
import io
from screeninfo import get_monitors

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{sys.argv[0]}"', None, 1)
    sys.exit()

console_window = win32console.GetConsoleWindow()
if console_window:
    win32gui.ShowWindow(console_window, 0)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class WindowManagerGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Window Workspace")
        self.geometry("360x540")
        self.resizable(False, False)
        
        self.file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
        self.width, self.height, self.always_on_top_val, self.countdown_val = self.load_config()
        
        self.pending_resize = False
        self.status_timer = None

        if self.always_on_top_val:
            self.attributes("-topmost", True)
        
        self.setup_ui()
        self.start_focus_tracker()

    def load_config(self):
        config = configparser.ConfigParser()
        if not os.path.exists(self.file_path):
            return 1920, 1080, False, 3
        try:
            config.read(self.file_path)
            w = int(config.get("Settings", "Width", fallback=1920))
            h = int(config.get("Settings", "Height", fallback=1080))
            ontop = config.getboolean("Settings", "AlwaysOnTop", fallback=False)
            countdown = int(config.get("Settings", "Countdown", fallback=3))
            return w, h, ontop, countdown
        except:
            return 1920, 1080, False, 3

    def save_config(self, w, h, ontop, countdown):
        config = configparser.ConfigParser()
        config["Settings"] = {
            "Width": str(w),
            "Height": str(h),
            "AlwaysOnTop": str(ontop),
            "Countdown": str(countdown)
        }
        try:
            with io.StringIO() as ss:
                config.write(ss)
                content = ss.getvalue().strip()
            with open(self.file_path, "w") as f:
                f.write(content)
            self.width, self.height, self.always_on_top_val, self.countdown_val = w, h, ontop, countdown
            self.update_config_label()
            return True
        except:
            return False

    def set_status(self, text, color="gray", auto_reset=True):
        if self.status_timer:
            self.after_cancel(self.status_timer)
            self.status_timer = None
            
        self.status_label.configure(text=text, text_color=color)
        
        if auto_reset:
            self.status_timer = self.after(5000, lambda: self.status_label.configure(text="READY", text_color="gray"))

    def toggle_always_on_top(self):
        is_on = self.topmost_check.get()
        self.attributes("-topmost", is_on)
        self.always_on_top_val = is_on
        if self.width and self.height:
            self.save_config(self.width, self.height, is_on, self.countdown_val)

    def update_cd_from_entry(self, *args):
        try:
            val = self.cd_entry.get()
            if val == "": return
            self.countdown_val = int(val)
            if self.width and self.height:
                self.save_config(self.width, self.height, self.always_on_top_val, self.countdown_val)
        except ValueError:
            pass

    # Feature: Aspect ratio string parser supporting multiple delimiters and zero-fallback
    def parse_ratio(self):
        ratio_str = self.ratio_combo.get().strip()
        if ratio_str in ("Free", "0", ""):
            return None
        
        if ":" in ratio_str:
            parts = ratio_str.split(":")
        else:
            parts = ratio_str.split()
            
        if len(parts) == 2:
            try:
                r_w = float(parts[0])
                r_h = float(parts[1])
                if r_w == 0 or r_h == 0:
                    return None
                return r_w, r_h
            except ValueError:
                return None
        return None

    # Feature: Interactive window resolution and customizable aspect ratio controller
    def update_res_from_ui(self, event=None, trigger=None):
        try:
            parsed = self.parse_ratio()
            if trigger == "width":
                w_val = self.width_entry.get()
                if not w_val: return
                w = int(w_val)
                if parsed:
                    r_w, r_h = parsed
                    h = int(w * r_h / r_w)
                    self.height_entry.delete(0, "end")
                    self.height_entry.insert(0, str(h))
                else:
                    h_val = self.height_entry.get()
                    h = int(h_val) if h_val else 0
            elif trigger == "height":
                h_val = self.height_entry.get()
                if not h_val: return
                h = int(h_val)
                if parsed:
                    r_w, r_h = parsed
                    w = int(h * r_w / r_h)
                    self.width_entry.delete(0, "end")
                    self.width_entry.insert(0, str(w))
                else:
                    w_val = self.width_entry.get()
                    w = int(w_val) if w_val else 0
            else:
                w_val = self.width_entry.get()
                if not w_val: return
                w = int(w_val)
                if parsed:
                    r_w, r_h = parsed
                    h = int(w * r_h / r_w)
                    self.height_entry.delete(0, "end")
                    self.height_entry.insert(0, str(h))
                else:
                    h_val = self.height_entry.get()
                    h = int(h_val) if h_val else 0

            if w > 0 and h > 0:
                self.save_config(w, h, self.always_on_top_val, self.countdown_val)
        except ValueError:
            pass

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        main_frame = ctk.CTkFrame(self, corner_radius=10)
        main_frame.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)

        monitor = get_monitors()[0]
        info_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        info_frame.grid(row=0, column=0, padx=10, pady=(8, 2), sticky="ew")
        info_frame.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkLabel(info_frame, text=f"Display: {monitor.width}x{monitor.height}", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w")
        self.config_label = ctk.CTkLabel(info_frame, text="", font=ctk.CTkFont(size=12, weight="bold"), text_color="#1F6AA5")
        self.config_label.grid(row=0, column=1, sticky="e")
        self.update_config_label()

        res_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        res_frame.grid(row=1, column=0, padx=10, pady=4, sticky="ew")
        res_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.width_entry = ctk.CTkEntry(res_frame, placeholder_text="Width", width=100, height=28)
        self.width_entry.grid(row=0, column=0, padx=2)
        self.width_entry.insert(0, str(self.width) if self.width else "")
        self.width_entry.bind("<KeyRelease>", lambda e: self.update_res_from_ui(e, "width"))

        self.height_entry = ctk.CTkEntry(res_frame, placeholder_text="Height", width=100, height=28)
        self.height_entry.grid(row=0, column=1, padx=2)
        self.height_entry.insert(0, str(self.height) if self.height else "")
        self.height_entry.bind("<KeyRelease>", lambda e: self.update_res_from_ui(e, "height"))

        # Feature: ComboBox for flexible built-in and custom aspect ratio selection
        self.ratio_combo = ctk.CTkComboBox(res_frame, values=["Free", "16:9", "4:3", "21:9"], width=100, height=28, command=lambda v: self.update_res_from_ui(None, "ratio"))
        self.ratio_combo.grid(row=0, column=2, padx=2)
        self.ratio_combo.set("Free")
        self.ratio_combo.bind("<KeyRelease>", lambda e: self.update_res_from_ui(e, "ratio"))

        self.focus_box = ctk.CTkTextbox(main_frame, height=35, corner_radius=8, fg_color="#2B2B2B", text_color="#2ECC71", font=ctk.CTkFont(size=12, weight="bold"))
        self.focus_box.grid(row=2, column=0, padx=10, pady=4, sticky="ew")
        self.focus_box.configure(state="disabled")

        ctrl_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        ctrl_frame.grid(row=3, column=0, padx=10, pady=4, sticky="ew")
        ctrl_frame.grid_columnconfigure(0, weight=1)

        self.topmost_check = ctk.CTkCheckBox(ctrl_frame, text="Pin Window", font=ctk.CTkFont(size=12), command=self.toggle_always_on_top)
        self.topmost_check.grid(row=0, column=0, sticky="w")
        if self.always_on_top_val: self.topmost_check.select()

        cd_inner = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        cd_inner.grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(cd_inner, text="Delay (s):", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 5))
        self.cd_entry = ctk.CTkEntry(cd_inner, width=45, height=24, font=ctk.CTkFont(size=12))
        self.cd_entry.insert(0, str(self.countdown_val))
        self.cd_entry.pack(side="left")
        self.cd_entry.bind("<KeyRelease>", self.update_cd_from_entry)

        act_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        act_frame.grid(row=4, column=0, padx=10, pady=4)
        
        btn_data = [
            ("Capture Layout", self.check_save, "#1F6AA5", True),
            ("Reload Config", self.reload_ui_config, "#4A4A4A", False),
            ("Apply Layout", self.resize_only, "#1F6AA5", True),
            ("Open Folder", self.open_folder, "#4A4A4A", False)
        ]

        for i, (txt, cmd, clr, use_delay) in enumerate(btn_data):
            r, c = divmod(i, 2)
            action = (lambda x=cmd: self.delayed_action(x)) if use_delay else cmd
            btn = ctk.CTkButton(act_frame, text=txt, width=140, height=32, corner_radius=6, fg_color=clr, command=action)
            btn.grid(row=r, column=c, padx=4, pady=4)

        pos_frame = ctk.CTkFrame(main_frame, corner_radius=8, fg_color="#333333")
        pos_frame.grid(row=5, column=0, padx=10, pady=8)
        
        symbols = [("↖", "1"), ("↑", "2"), ("↗", "3"), ("←", "4"), ("•", "5"), ("→", "6"), ("↙", "7"), ("↓", "8"), ("↘", "9")]
        for i, (sym, cmd) in enumerate(symbols):
            r, c = divmod(i, 3)
            btn = ctk.CTkButton(pos_frame, text=sym, width=55, height=55, font=ctk.CTkFont(size=24, weight="bold"), fg_color="#1F6AA5", corner_radius=8, command=lambda m=cmd: self.delayed_action(lambda: self.move_window(m)))
            btn.grid(row=r, column=c, padx=3, pady=3)

        self.status_label = ctk.CTkLabel(main_frame, text="READY", font=ctk.CTkFont(size=15, weight="bold"), text_color="gray")
        self.status_label.grid(row=6, column=0, pady=(2, 10))

    def update_config_label(self):
        val = f"{self.width}x{self.height}" if self.width else "None"
        self.config_label.configure(text=f"[{val}]")

    def get_active_process_name(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return psutil.Process(pid).name()
        except:
            return "Unknown"

    def update_focus_display(self, exe_name):
        self.focus_box.configure(state="normal")
        self.focus_box.delete("1.0", "end")
        self.focus_box.insert("1.0", f"> {exe_name}")
        self.focus_box.configure(state="disabled")

    def start_focus_tracker(self):
        def track():
            while True:
                try:
                    exe = self.get_active_process_name()
                    self.after(0, lambda e=exe: self.update_focus_display(e))
                except: pass
                time.sleep(0.5)
        threading.Thread(target=track, daemon=True).start()

    def delayed_action(self, action_func):
        def countdown():
            wait_time = self.countdown_val
            for i in range(wait_time, 0, -1):
                self.after(0, lambda x=i: self.set_status(f"WAITING... {x}s", "#E67E22", auto_reset=False))
                time.sleep(1)
            self.after(0, action_func)
        threading.Thread(target=countdown, daemon=True).start()

    def check_save(self):
        active = gw.getActiveWindow()
        if active and active.title != self.title():
            if self.save_config(active.width, active.height, self.always_on_top_val, self.countdown_val):
                self.pending_resize = True
                self.width_entry.delete(0, "end")
                self.width_entry.insert(0, str(active.width))
                self.height_entry.delete(0, "end")
                self.height_entry.insert(0, str(active.height))
                self.ratio_combo.set("Free")
                self.set_status(f"CAPTURED: {active.width}x{active.height}", "#2ECC71")
        else:
            self.set_status("ERROR: NO TARGET", "#E74C3C")

    def reload_ui_config(self):
        self.width, self.height, self.always_on_top_val, self.countdown_val = self.load_config()
        self.width_entry.delete(0, "end")
        self.width_entry.insert(0, str(self.width))
        self.height_entry.delete(0, "end")
        self.height_entry.insert(0, str(self.height))
        self.ratio_combo.set("Free")
        self.cd_entry.delete(0, "end")
        self.cd_entry.insert(0, str(self.countdown_val))
        self.attributes("-topmost", self.always_on_top_val)
        if self.always_on_top_val: self.topmost_check.select()
        else: self.topmost_check.deselect()
        self.update_config_label()
        self.set_status("CONFIG RELOADED")

    def resize_only(self):
        if not self.width: return
        active = gw.getActiveWindow()
        if active:
            active.restore()
            active.resizeTo(self.width, self.height)
            self.pending_resize = False
            self.set_status("LAYOUT APPLIED", "#2ECC71")

    def get_window_offsets(self, hwnd):
        rect = wintypes.RECT()
        ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect))
        win_rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(win_rect))
        return rect.left - win_rect.left, rect.top - win_rect.top, win_rect.right - rect.right, win_rect.bottom - rect.bottom

    def move_window(self, pos_key):
        active = gw.getActiveWindow()
        if active:
            if self.pending_resize and self.width:
                active.restore()
                active.resizeTo(self.width, self.height)
                self.pending_resize = False
                msg = "RESIZED & MOVED"
            else:
                msg = "POSITION UPDATED"

            monitor = get_monitors()[0]
            sw, sh = monitor.width, monitor.height
            hwnd = active._hWnd

            l_off, t_off, r_off, b_off = self.get_window_offsets(hwnd)
            
            real_w = active.width - l_off - r_off
            real_h = active.height - t_off - b_off

            cx, cy = (sw - real_w) // 2, (sh - real_h) // 2
            
            coords = {
                "1": (0, 0), "2": (cx, 0), "3": (sw - real_w, 0),
                "4": (0, cy), "5": (cx, cy), "6": (sw - real_w, cy),
                "7": (0, sh - real_h), "8": (cx, sh - real_h), "9": (sw - real_w, sh - real_h)
            }
            
            nx, ny = coords[pos_key]
            
            active.restore()
            active.moveTo(nx - l_off, ny - t_off)
            self.set_status(msg, "#2ECC71")

    def open_folder(self):
        os.startfile(os.path.dirname(os.path.abspath(__file__)))
        self.set_status("FOLDER OPENED")

if __name__ == "__main__":
    app = WindowManagerGUI()
    app.mainloop()
