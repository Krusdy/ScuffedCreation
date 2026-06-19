import customtkinter as ctk
import os
import time
import threading
import pygetwindow as gw
import psutil
import win32process
import win32gui
import win32api
import win32console
import sys
import ctypes
import configparser
import io

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    pass

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
        
        app_width = 380
        app_height = 800
        
        monitor_info = win32api.GetMonitorInfo(win32api.MonitorFromPoint((0, 0)))
        work_area = monitor_info['Work']
        screen_width = work_area[2] - work_area[0]
        screen_height = work_area[3] - work_area[1]
        x = work_area[0] + int((screen_width / 2) - (app_width / 2))
        y = work_area[1] + int((screen_height / 2) - (app_height / 2))
        
        self.geometry(f"{app_width}x{app_height}+{x}+{y}")
        self.resizable(False, False)
        
        self.file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
        self.presets = {}
        self.width, self.height, self.always_on_top_val, self.countdown_val = self.load_config()
        
        self.pending_resize = False
        self.status_timer = None
        
        self.preset_undo_stack = []
        self.preset_redo_stack = []
        self.last_preset_text = ""
        self.editing_inline = None

        if self.always_on_top_val:
            self.attributes("-topmost", True)
            
        self.bind_class("Entry", "<Control-BackSpace>", self._ctrl_bs)
        self.bind("<Control-s>", self._save_preset_event)
        self.bind("<Control-S>", self._save_preset_event)
        
        self.setup_ui()
        self.start_focus_tracker()

    def _ctrl_bs(self, event):
        w = event.widget
        try:
            if w.select_present():
                w.delete("sel.first", "sel.last")
            else:
                idx = w.index("insert")
                text = w.get()[:idx].rstrip()
                del_idx = text.rfind(" ") + 1 if " " in text else 0
                w.delete(del_idx, idx)
            return "break"
        except: pass

    def load_config(self):
        config = configparser.ConfigParser()
        config.optionxform = str
        if not os.path.exists(self.file_path):
            return 1920, 1080, False, 3
        try:
            config.read(self.file_path)
            w = int(config.get("Settings", "Width", fallback=1920))
            h = int(config.get("Settings", "Height", fallback=1080))
            ontop = config.getboolean("Settings", "AlwaysOnTop", fallback=False)
            countdown = int(config.get("Settings", "Countdown", fallback=3))
            if config.has_section("Presets"):
                self.presets = dict(config.items("Presets"))
            return w, h, ontop, countdown
        except:
            return 1920, 1080, False, 3

    def save_config(self, w, h, ontop, countdown):
        config = configparser.ConfigParser()
        config.optionxform = str
        config["Settings"] = {"Width": str(w), "Height": str(h), "AlwaysOnTop": str(ontop), "Countdown": str(countdown)}
        config["Presets"] = self.presets
        try:
            with io.StringIO() as ss:
                config.write(ss)
                content = ss.getvalue().strip()
            with open(self.file_path, "w") as f: f.write(content)
            self.width, self.height, self.always_on_top_val, self.countdown_val = w, h, ontop, countdown
            self.update_config_label()
            return True
        except: return False

    def _save_preset_event(self, event=None):
        self.save_preset()

    def save_preset(self):
        name = self.preset_name_entry.get().strip()
        w = self.width_entry.get()
        h = self.height_entry.get()
        if name and w and h:
            self.presets[name] = f"{w},{h}"
            self.save_config(self.width, self.height, self.always_on_top_val, self.countdown_val)
            self.update_preset_list()
            self.preset_name_entry.delete(0, "end")
            self.preset_undo_stack.clear()
            self.preset_redo_stack.clear()
            self.last_preset_text = ""
            self.set_status(f"Preset '{name}' Saved", "#2ECC71")

    def load_preset_to_ui(self, name):
        if name in self.presets:
            w, h = self.presets[name].split(",")
            self.width_entry.delete(0, "end"); self.width_entry.insert(0, w)
            self.height_entry.delete(0, "end"); self.height_entry.insert(0, h)
            self.update_res_from_ui()
            self.set_status(f"Loaded '{name}'")

    def delete_preset(self, name):
        if name in self.presets:
            del self.presets[name]
            self.save_config(self.width, self.height, self.always_on_top_val, self.countdown_val)
            self.update_preset_list()
            self.set_status(f"Deleted '{name}'", "#E74C3C")

    def rename_preset(self, old_name):
        self.editing_inline = old_name
        self.update_preset_list()

    def update_preset_list(self):
        for widget in self.presets_frame.winfo_children(): 
            widget.destroy()
            
        for name, res in self.presets.items():
            row_frame = ctk.CTkFrame(self.presets_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)
            
            if getattr(self, "editing_inline", None) == name:
                entry = ctk.CTkEntry(row_frame, height=32)
                entry.insert(0, name)
                entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
                
                def save_inline(old=name, e=entry):
                    new_name = e.get().strip()
                    if new_name and new_name != old:
                        new_presets = {}
                        for k, v in self.presets.items():
                            if k == old: new_presets[new_name] = v
                            else: new_presets[k] = v
                        self.presets = new_presets
                        self.save_config(self.width, self.height, self.always_on_top_val, self.countdown_val)
                    self.editing_inline = None
                    self.update_preset_list()
                    if new_name: self.set_status(f"Renamed to '{new_name}'", "#2ECC71")
                
                entry.bind("<Return>", lambda e, old=name, ent=entry: save_inline(old, ent))
                entry.bind("<Escape>", lambda e: [setattr(self, 'editing_inline', None), self.update_preset_list()])
                ctk.CTkButton(row_frame, text="✓", width=32, height=32, fg_color="#2ECC71", hover_color="#27AE60", command=save_inline).pack(side="right")
                
                entry.focus_set()
                entry.select_range(0, 'end')
                
            else:
                btn = ctk.CTkButton(row_frame, text=f"{name} ({res})", height=32, anchor="w", fg_color="#2C3E50", hover_color="#34495E", command=lambda n=name: self.load_preset_to_ui(n))
                btn.pack(fill="x", expand=True)
                
                menu = ctk.CTkOptionMenu(self, values=["Rename", "Delete"], command=lambda v, n=name: self._menu_handler(v, n))
                btn.bind("<Button-3>", lambda e, m=menu: m._dropdown_menu.tk_popup(e.x_root, e.y_root))

    def _menu_handler(self, value, name):
        if value == "Rename": self.rename_preset(name)
        elif value == "Delete": self.delete_preset(name)

    def set_status(self, text, color="gray", auto_reset=True):
        if self.status_timer: self.after_cancel(self.status_timer); self.status_timer = None
        self.status_label.configure(text=text, text_color=color)
        if auto_reset: self.status_timer = self.after(5000, lambda: self.status_label.configure(text="Ready", text_color="gray"))

    def toggle_always_on_top(self):
        is_on = self.topmost_check.get()
        self.attributes("-topmost", is_on)
        self.always_on_top_val = is_on
        if self.width and self.height: self.save_config(self.width, self.height, is_on, self.countdown_val)

    def update_cd_from_entry(self, *args):
        try:
            val = self.cd_entry.get()
            if val == "": return
            self.countdown_val = int(val)
            if self.width and self.height: self.save_config(self.width, self.height, self.always_on_top_val, self.countdown_val)
        except ValueError: pass

    def parse_ratio(self):
        ratio_str = self.ratio_combo.get().strip()
        if ratio_str in ("Free", "0", ""): return None
        parts = ratio_str.split(":") if ":" in ratio_str else ratio_str.split()
        if len(parts) == 2:
            try: return float(parts[0]), float(parts[1])
            except ValueError: return None
        return None

    def update_res_from_ui(self, event=None, trigger=None):
        try:
            parsed = self.parse_ratio()
            w, h = 0, 0
            if trigger == "width":
                w = int(self.width_entry.get() or 0)
                if parsed: h = int(w * parsed[1] / parsed[0]); self.height_entry.delete(0, "end"); self.height_entry.insert(0, str(h))
                else: h = int(self.height_entry.get() or 0)
            elif trigger == "height":
                h = int(self.height_entry.get() or 0)
                if parsed: w = int(h * parsed[0] / parsed[1]); self.width_entry.delete(0, "end"); self.width_entry.insert(0, str(w))
                else: w = int(self.width_entry.get() or 0)
            else:
                w = int(self.width_entry.get() or 0)
                h = int(self.height_entry.get() or 0)
            if w > 0 and h > 0: self.save_config(w, h, self.always_on_top_val, self.countdown_val)
        except ValueError: pass

    def _track_preset_text(self, event):
        if event.keysym in ("Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R", "Return"):
            return
        current = self.preset_name_entry.get()
        if current != self.last_preset_text:
            self.preset_undo_stack.append(self.last_preset_text)
            self.preset_redo_stack.clear()
            self.last_preset_text = current

    def _undo_preset_text(self, event):
        if self.preset_undo_stack:
            self.preset_redo_stack.append(self.last_preset_text)
            prev = self.preset_undo_stack.pop()
            self.preset_name_entry.delete(0, "end")
            self.preset_name_entry.insert(0, prev)
            self.last_preset_text = prev
        return "break"

    def _redo_preset_text(self, event):
        if self.preset_redo_stack:
            self.preset_undo_stack.append(self.last_preset_text)
            nxt = self.preset_redo_stack.pop()
            self.preset_name_entry.delete(0, "end")
            self.preset_name_entry.insert(0, nxt)
            self.last_preset_text = nxt
        return "break"

    def setup_ui(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        monitor_info = win32api.GetMonitorInfo(win32api.MonitorFromPoint((0, 0)))
        work_area = monitor_info['Work']
        mw = work_area[2] - work_area[0]
        mh = work_area[3] - work_area[1]
        
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(header_frame, text=f"Display: {mw}x{mh}", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        self.config_label = ctk.CTkLabel(header_frame, text="", font=ctk.CTkFont(size=14, weight="bold"), text_color="#1F6AA5")
        self.config_label.pack(side="right")
        self.update_config_label()
        
        card_res = ctk.CTkFrame(main_frame, corner_radius=10)
        card_res.pack(fill="x", pady=5)
        res_inner = ctk.CTkFrame(card_res, fg_color="transparent")
        res_inner.pack(padx=10, pady=12, fill="x")
        res_inner.grid_columnconfigure((0, 1, 2), weight=1)
        self.width_entry = ctk.CTkEntry(res_inner, placeholder_text="Width", height=32)
        self.width_entry.grid(row=0, column=0, padx=(0, 5), sticky="we")
        self.width_entry.insert(0, str(self.width)); self.width_entry.bind("<KeyRelease>", lambda e: self.update_res_from_ui(e, "width"))
        self.height_entry = ctk.CTkEntry(res_inner, placeholder_text="Height", height=32)
        self.height_entry.grid(row=0, column=1, padx=5, sticky="we")
        self.height_entry.insert(0, str(self.height)); self.height_entry.bind("<KeyRelease>", lambda e: self.update_res_from_ui(e, "height"))
        self.ratio_combo = ctk.CTkComboBox(res_inner, values=["Free", "16:9", "4:3", "21:9"], height=32, command=lambda v: self.update_res_from_ui(None, "ratio"))
        self.ratio_combo.grid(row=0, column=2, padx=(5, 0), sticky="we"); self.ratio_combo.set("Free")

        ctrl_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        ctrl_frame.pack(fill="x", pady=8)
        self.topmost_check = ctk.CTkCheckBox(ctrl_frame, text="Always On Top", font=ctk.CTkFont(size=13), command=self.toggle_always_on_top)
        self.topmost_check.pack(side="left", padx=5)
        if self.always_on_top_val: self.topmost_check.select()
        ctk.CTkLabel(ctrl_frame, text="Delay (s):", font=ctk.CTkFont(size=13)).pack(side="left", padx=(15, 5))
        self.cd_entry = ctk.CTkEntry(ctrl_frame, width=50, height=28); self.cd_entry.insert(0, str(self.countdown_val))
        self.cd_entry.pack(side="left"); self.cd_entry.bind("<KeyRelease>", self.update_cd_from_entry)

        act_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        act_frame.pack(fill="x", pady=5)
        act_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(act_frame, text="Capture", height=36, font=ctk.CTkFont(size=14, weight="bold"), fg_color="#1F6AA5", command=lambda: self.delayed_action(self.check_save)).grid(row=0, column=0, padx=5, pady=5, sticky="we")
        ctk.CTkButton(act_frame, text="Apply", height=36, font=ctk.CTkFont(size=14, weight="bold"), fg_color="#1F6AA5", command=lambda: self.delayed_action(self.resize_only)).grid(row=0, column=1, padx=5, pady=5, sticky="we")

        self.focus_box = ctk.CTkTextbox(main_frame, height=36, corner_radius=8, fg_color="#2B2B2B", text_color="#2ECC71", font=ctk.CTkFont(size=13, weight="bold"))
        self.focus_box.pack(fill="x", pady=8); self.focus_box.configure(state="disabled")

        pos_frame = ctk.CTkFrame(main_frame, corner_radius=12, fg_color="#2B2B2B")
        pos_frame.pack(pady=10) 
        
        symbols = [("↖", "1"), ("↑", "2"), ("↗", "3"), ("←", "4"), ("•", "5"), ("→", "6"), ("↙", "7"), ("↓", "8"), ("↘", "9")]
        for i, (sym, cmd) in enumerate(symbols):
            r, c = divmod(i, 3)
            ctk.CTkButton(pos_frame, text=sym, width=64, height=64, font=ctk.CTkFont(size=32, weight="bold"), 
                          fg_color="#1F6AA5", corner_radius=8, 
                          command=lambda m=cmd: self.delayed_action(lambda: self.move_window(m))
                         ).grid(row=r, column=c, padx=6, pady=6)

        card_presets = ctk.CTkFrame(main_frame, corner_radius=10)
        card_presets.pack(fill="both", expand=True, pady=5)
        preset_top = ctk.CTkFrame(card_presets, fg_color="transparent")
        preset_top.pack(fill="x", padx=10, pady=(12, 5))
        self.preset_name_entry = ctk.CTkEntry(preset_top, placeholder_text="Preset Name...", height=32)
        self.preset_name_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        self.preset_name_entry.bind("<KeyRelease>", self._track_preset_text)
        self.preset_name_entry.bind("<Control-z>", self._undo_preset_text)
        self.preset_name_entry.bind("<Control-y>", self._redo_preset_text)
        self.preset_name_entry.bind("<Return>", self._save_preset_event)
        
        ctk.CTkButton(preset_top, text="Save", width=70, height=32, font=ctk.CTkFont(weight="bold"), command=self.save_preset).pack(side="right")
        self.presets_frame = ctk.CTkScrollableFrame(card_presets, fg_color="transparent")
        self.presets_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.update_preset_list()
        
        self.status_label = ctk.CTkLabel(main_frame, text="Ready", font=ctk.CTkFont(size=14, weight="bold"), text_color="gray")
        self.status_label.pack(pady=(5, 0))

    def update_config_label(self):
        val = f"{self.width}x{self.height}" if self.width else "None"
        self.config_label.configure(text=f"[{val}]")

    def get_active_process_name(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return psutil.Process(pid).name()
        except: return "Unknown"

    def update_focus_display(self, exe_name):
        self.focus_box.configure(state="normal"); self.focus_box.delete("1.0", "end"); self.focus_box.insert("1.0", f"> {exe_name}"); self.focus_box.configure(state="disabled")

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
            for i in range(self.countdown_val, 0, -1):
                self.after(0, lambda x=i: self.set_status(f"Waiting... {x}s", "#E67E22", auto_reset=False)); time.sleep(1)
            self.after(0, action_func)
        threading.Thread(target=countdown, daemon=True).start()

    def check_save(self):
        active = gw.getActiveWindow()
        if active and active.title != self.title():
            if self.save_config(active.width, active.height, self.always_on_top_val, self.countdown_val):
                self.pending_resize = True
                self.width_entry.delete(0, "end"); self.width_entry.insert(0, str(active.width))
                self.height_entry.delete(0, "end"); self.height_entry.insert(0, str(active.height))
                self.set_status(f"Captured: {active.width}x{active.height}", "#2ECC71")
        else: self.set_status("Error: No Target", "#E74C3C")

    def reload_ui_config(self):
        self.width, self.height, self.always_on_top_val, self.countdown_val = self.load_config()
        self.width_entry.delete(0, "end"); self.width_entry.insert(0, str(self.width))
        self.height_entry.delete(0, "end"); self.height_entry.insert(0, str(self.height))
        self.update_preset_list(); self.update_config_label(); self.set_status("Reloaded")

    def resize_only(self):
        active = gw.getActiveWindow()
        if active: active.restore(); active.resizeTo(self.width, self.height); self.set_status("Applied", "#2ECC71")

    def move_window(self, pos_key):
        active = gw.getActiveWindow()
        if active:
            hwnd = active._hWnd
            monitor_info = win32api.GetMonitorInfo(win32api.MonitorFromWindow(hwnd))
            work_area = monitor_info['Work']
            
            start_x = work_area[0]
            start_y = work_area[1]
            sw = work_area[2] - work_area[0]
            sh = work_area[3] - work_area[1]
            
            aw = active.width
            ah = active.height
            
            cx = start_x + (sw - aw) // 2
            cy = start_y + (sh - ah) // 2
            
            coords = {
                "1": (start_x, start_y), 
                "2": (cx, start_y), 
                "3": (start_x + sw - aw, start_y), 
                "4": (start_x, cy), 
                "5": (cx, cy), 
                "6": (start_x + sw - aw, cy), 
                "7": (start_x, start_y + sh - ah), 
                "8": (cx, start_y + sh - ah), 
                "9": (start_x + sw - aw, start_y + sh - ah)
            }
            nx, ny = coords[pos_key]
            active.restore()
            active.moveTo(nx, ny)
            self.set_status("Moved", "#2ECC71")

    def open_folder(self): os.startfile(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    app = WindowManagerGUI()
    app.mainloop()
