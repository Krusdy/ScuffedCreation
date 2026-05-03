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

        self.title("Window Manager")
        self.geometry("450x600")
        self.resizable(False, False)
        
        self.file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
        self.width, self.height, self.always_on_top_val, self.countdown_val = self.load_config()
        
        if self.always_on_top_val:
            self.attributes("-topmost", True)
            
        self.setup_ui()
        self.start_focus_tracker()

    def load_config(self):
        config = configparser.ConfigParser()
        if not os.path.exists(self.file_path):
            return None, None, False, 3
        try:
            config.read(self.file_path)
            w = int(config.get("Settings", "Width"))
            h = int(config.get("Settings", "Height"))
            ontop = config.getboolean("Settings", "AlwaysOnTop", fallback=False)
            countdown = int(config.get("Settings", "Countdown", fallback=3))
            return w, h, ontop, countdown
        except:
            return None, None, False, 3

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

    def toggle_always_on_top(self):
        is_on = self.topmost_check.get()
        self.attributes("-topmost", is_on)
        self.always_on_top_val = is_on
        if self.width and self.height:
            self.save_config(self.width, self.height, is_on, self.countdown_val)

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_frame = ctk.CTkFrame(self, corner_radius=15)
        main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        main_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(main_frame, text="SYSTEM INFORMATION", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, pady=(20, 10))
        
        monitor = get_monitors()[0]
        self.info_label = ctk.CTkLabel(main_frame, text=f"Display: {monitor.width}x{monitor.height}", font=ctk.CTkFont(size=12))
        self.info_label.grid(row=1, column=0, padx=20, sticky="w")
        
        self.config_label = ctk.CTkLabel(main_frame, text="", font=ctk.CTkFont(size=12))
        self.update_config_label()
        self.config_label.grid(row=1, column=1, padx=20, sticky="e")

        self.topmost_check = ctk.CTkCheckBox(main_frame, text="Always on Top", font=ctk.CTkFont(size=12), command=self.toggle_always_on_top)
        self.topmost_check.grid(row=2, column=0, columnspan=2, pady=10)
        if self.always_on_top_val:
            self.topmost_check.select()

        ctk.CTkLabel(main_frame, text="CURRENT PROCESS (.EXE)", font=ctk.CTkFont(size=14, weight="bold")).grid(row=3, column=0, columnspan=2, pady=(10, 5))
        
        self.focus_box = ctk.CTkTextbox(main_frame, height=40, corner_radius=10, fg_color="#2B2B2B", text_color="#1F6AA5", font=ctk.CTkFont(size=13, weight="bold"))
        self.focus_box.grid(row=4, column=0, columnspan=2, padx=20, pady=5, sticky="ew")
        self.focus_box.configure(state="disabled")

        action_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        action_frame.grid(row=5, column=0, columnspan=2, pady=15)

        ctk.CTkButton(action_frame, text="Check & Save", width=120, corner_radius=8, command=lambda: self.delayed_action(self.check_save)).grid(row=0, column=0, padx=5, pady=5)
        ctk.CTkButton(action_frame, text="Reload Config", width=120, corner_radius=8, fg_color="#4A4A4A", hover_color="#5A5A5A", command=self.reload_ui_config).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkButton(action_frame, text="Resize Only", width=250, corner_radius=8, command=lambda: self.delayed_action(self.resize_only)).grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        pos_frame = ctk.CTkFrame(main_frame, corner_radius=10, fg_color="#333333")
        pos_frame.grid(row=6, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        pos_frame.grid_columnconfigure((0, 1), weight=1)

        positions = [("Top-Left", "1"), ("Top-Right", "2"), ("Bottom-Left", "3"), ("Bottom-Right", "4"), ("Center", "5")]
        for i, (name, cmd) in enumerate(positions):
            r, c = divmod(i, 2)
            span = 2 if i == 4 else 1
            btn = ctk.CTkButton(pos_frame, text=name, height=32, corner_radius=6, fg_color="#1F6AA5", command=lambda m=cmd: self.delayed_action(lambda: self.move_window(m)))
            btn.grid(row=r, column=c, columnspan=span, padx=10, pady=8, sticky="ew")

        self.status_label = ctk.CTkLabel(main_frame, text="Status: Ready", font=ctk.CTkFont(size=12, slant="italic"), text_color="gray")
        self.status_label.grid(row=7, column=0, columnspan=2, pady=(10, 20))

    def update_config_label(self):
        val = f"{self.width}x{self.height}" if self.width else "None"
        self.config_label.configure(text=f"Config: {val} | CD: {self.countdown_val}s")

    def get_active_process_name(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            return process.name()
        except:
            return "Unknown"

    def update_focus_display(self, exe_name):
        self.focus_box.configure(state="normal")
        self.focus_box.delete("1.0", "end")
        self.focus_box.insert("1.0", f" > {exe_name}")
        self.focus_box.configure(state="disabled")

    def start_focus_tracker(self):
        def track():
            while True:
                try:
                    exe_name = self.get_active_process_name()
                    self.after(0, lambda e=exe_name: self.update_focus_display(e))
                except: pass
                time.sleep(0.5)
        threading.Thread(target=track, daemon=True).start()

    def delayed_action(self, action_func):
        def countdown():
            for i in range(self.countdown_val, 0, -1):
                self.after(0, lambda x=i: self.status_label.configure(text=f"Status: Action in {x}s...", text_color="#E67E22"))
                time.sleep(1)
            self.after(0, action_func)
        threading.Thread(target=countdown, daemon=True).start()

    def check_save(self):
        active = gw.getActiveWindow()
        if active and active.title != self.title():
            if self.save_config(active.width, active.height, self.always_on_top_val, self.countdown_val):
                self.status_label.configure(text=f"Status: Saved {active.width}x{active.height}", text_color="#2ECC71")
        else:
            self.status_label.configure(text="Status: Error - Target not focused", text_color="#E74C3C")

    def reload_ui_config(self):
        self.width, self.height, self.always_on_top_val, self.countdown_val = self.load_config()
        self.attributes("-topmost", self.always_on_top_val)
        if self.always_on_top_val: self.topmost_check.select()
        else: self.topmost_check.deselect()
        self.update_config_label()
        self.status_label.configure(text="Status: Config Reloaded", text_color="gray")

    def resize_only(self):
        if not self.width: return
        active = gw.getActiveWindow()
        if active:
            active.restore()
            active.resizeTo(self.width, self.height)
            self.status_label.configure(text="Status: Resized Successfully", text_color="#2ECC71")

    def move_window(self, pos_key):
        if not self.width: return
        active = gw.getActiveWindow()
        if active:
            monitor = get_monitors()[0]
            sw, sh = monitor.width, monitor.height
            nx, ny = 0, 0
            if pos_key == "1": nx, ny = 0, 0
            elif pos_key == "2": nx, ny = sw - self.width, 0
            elif pos_key == "3": nx, ny = 0, sh - self.height
            elif pos_key == "4": nx, ny = sw - self.width, sh - self.height
            elif pos_key == "5": nx, ny = (sw//2)-(self.width//2), (sh//2)-(self.height//2)
            
            active.restore()
            active.resizeTo(self.width, self.height)
            active.moveTo(nx, ny)
            self.status_label.configure(text="Status: Moved & Resized", text_color="#2ECC71")

if __name__ == "__main__":
    app = WindowManagerGUI()
    app.mainloop()
