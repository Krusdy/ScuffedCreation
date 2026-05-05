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
        self.title("Window Workspace")
        self.geometry("360x480")
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

        self.focus_box = ctk.CTkTextbox(main_frame, height=35, corner_radius=8, fg_color="#2B2B2B", text_color="#2ECC71", font=ctk.CTkFont(size=12, weight="bold"))
        self.focus_box.grid(row=1, column=0, padx=10, pady=4, sticky="ew")
        self.focus_box.configure(state="disabled")

        ctrl_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        ctrl_frame.grid(row=2, column=0, padx=10, pady=4, sticky="ew")
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
        act_frame.grid(row=3, column=0, padx=10, pady=4)
        
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
        pos_frame.grid(row=4, column=0, padx=10, pady=8)
        
        symbols = [("↖", "1"), ("↑", "2"), ("↗", "3"), ("←", "4"), ("•", "5"), ("→", "6"), ("↙", "7"), ("↓", "8"), ("↘", "9")]
        for i, (sym, cmd) in enumerate(symbols):
            r, c = divmod(i, 3)
            btn = ctk.CTkButton(pos_frame, text=sym, width=55, height=55, font=ctk.CTkFont(size=24, weight="bold"), fg_color="#1F6AA5", corner_radius=8, command=lambda m=cmd: self.delayed_action(lambda: self.move_window(m)))
            btn.grid(row=r, column=c, padx=3, pady=3)

        self.status_label = ctk.CTkLabel(main_frame, text="READY", font=ctk.CTkFont(size=15, weight="bold"), text_color="gray")
        self.status_label.grid(row=5, column=0, pady=(2, 10))

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
                self.set_status(f"CAPTURED: {active.width}x{active.height}", "#2ECC71")
        else:
            self.set_status("ERROR: NO TARGET", "#E74C3C")

    def reload_ui_config(self):
        self.width, self.height, self.always_on_top_val, self.countdown_val = self.load_config()
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

    def move_window(self, pos_key):
        active = gw.getActiveWindow()
        if active:
            monitor = get_monitors()[0]
            sw, sh = monitor.width, monitor.height
            
            if self.pending_resize and self.width:
                w, h = self.width, self.height
                active.restore()
                active.resizeTo(w, h)
                self.pending_resize = False
                msg = "RESIZED & MOVED"
            else:
                w, h = active.width, active.height
                msg = "POSITION UPDATED"

            cx, cy = (sw - w) // 2, (sh - h) // 2
            coords = {
                "1": (0, 0), "2": (cx, 0), "3": (sw - w, 0),
                "4": (0, cy), "5": (cx, cy), "6": (sw - w, cy),
                "7": (0, sh - h), "8": (cx, sh - h), "9": (sw - w, sh - h)
            }
            nx, ny = coords[pos_key]
            active.restore()
            active.moveTo(nx, ny)
            self.set_status(msg, "#2ECC71")

    def open_folder(self):
        os.startfile(os.path.dirname(os.path.abspath(__file__)))
        self.set_status("FOLDER OPENED")

if __name__ == "__main__":
    app = WindowManagerGUI()
    app.mainloop()
