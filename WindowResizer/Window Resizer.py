import customtkinter as ctk
import tkinter as tk
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
from ctypes import wintypes
import configparser
import io
import json
import logging
import traceback

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "error.log")

logger = logging.getLogger()
logger.setLevel(logging.ERROR)
handler = logging.FileHandler(LOG_FILE, delay=True)
formatter = logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

def log_exception(context="General"):
    logging.error(f"Critical Exception in {context}:\n{traceback.format_exc()}")

try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_int(-4))
except AttributeError:
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
        
        app_width = 1002
        app_height = 664
        
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_position = int((screen_width / 2) - (app_width / 2))
        y_position = int((screen_height / 2) - (app_height / 2))
        self.geometry(f"{app_width}x{app_height}+{x_position}+{y_position}")
        self.resizable(True, True)
        self.minsize(1002, 664)
        
        self.file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
        self.presets = {}
        self.autosets = []
        self.is_resizing = False
        self.resize_timer = None
        self.width, self.height, self.always_on_top_val, self.countdown_val, self.column1_width, self.column2_width, self.column3_width = self.load_config()
        
        self.pending_resize = False
        self.status_timer = None
        self.preset_undo_stack = []
        self.preset_redo_stack = []
        self.last_preset_text = ""
        self.editing_inline = None
        
        self.pid_cache = {} 
        
        if self.always_on_top_val:
            self.attributes("-topmost", True)
            
        self.bind_class("Entry", "<Control-BackSpace>", self._ctrl_backspace)
        self.bind("<Control-s>", self._save_preset_event)
        self.bind("<Configure>", self._on_window_configure)
        
        self.setup_ui()
        self.start_focus_tracker()
        self.start_auto_enforcer()

    def _on_window_configure(self, event):
        if event.widget == self:
            self.is_resizing = True
            if self.resize_timer:
                self.after_cancel(self.resize_timer)
            self.resize_timer = self.after(300, self.stop_window_resize)

    def stop_window_resize(self):
        self.is_resizing = False

    def start_paned_resize(self, event):
        if self.paned_window.identify(event.x, event.y):
            self.is_resizing = True

    def stop_paned_resize(self, event):
        self.is_resizing = False
        self.save_config()

    def _ctrl_backspace(self, event):
        widget = event.widget
        try:
            if widget.select_present():
                widget.delete("sel.first", "sel.last")
            else:
                idx = widget.index("insert")
                text = widget.get()[:idx].rstrip()
                del_idx = text.rfind(" ") + 1 if " " in text else 0
                widget.delete(del_idx, idx)
            return "break"
        except: pass

    def load_config(self):
        config = configparser.ConfigParser()
        config.optionxform = str
        if not os.path.exists(self.file_path):
            return 1920, 1080, False, 3, 280, 280, 418
        try:
            config.read(self.file_path)
            width = int(config.get("Settings", "Width", fallback=1920))
            height = int(config.get("Settings", "Height", fallback=1080))
            always_on_top = config.getboolean("Settings", "AlwaysOnTop", fallback=False)
            countdown = int(config.get("Settings", "Countdown", fallback=3))
            column1_val = int(config.get("Settings", "Column1Width", fallback=280))
            column2_val = int(config.get("Settings", "Column2Width", fallback=280))
            column3_val = int(config.get("Settings", "Column3Width", fallback=418))
            
            autosets_string = config.get("Settings", "AutoSets", fallback="[]")
            try:
                raw_autosets = json.loads(autosets_string)
                self.autosets = []
                for rule in raw_autosets:
                    self.autosets.append({
                        "executable": rule.get("executable", rule.get("exe", "")),
                        "width": rule.get("width", rule.get("w", 0)),
                        "height": rule.get("height", rule.get("h", 0)),
                        "x_position": rule.get("x_position", rule.get("x", 0)),
                        "y_position": rule.get("y_position", rule.get("y", 0)),
                        "automatic_position": rule.get("automatic_position", rule.get("pos", False)),
                        "automatic_size": rule.get("automatic_size", rule.get("size", False)),
                        "trigger": rule.get("trigger", "On Focus")
                    })
            except:
                self.autosets = []
                
            if config.has_section("Presets"):
                self.presets = dict(config.items("Presets"))
            return width, height, always_on_top, countdown, column1_val, column2_val, column3_val
        except:
            return 1920, 1080, False, 3, 280, 280, 418

    def save_config(self):
        config = configparser.ConfigParser()
        config.optionxform = str
        config["Settings"] = {
            "Width": str(self.width),
            "Height": str(self.height),
            "AlwaysOnTop": str(self.always_on_top_val),
            "Countdown": str(self.countdown_val),
            "Column1Width": str(self.column1_width),
            "Column2Width": str(self.column2_width),
            "Column3Width": str(self.column3_width),
            "AutoSets": json.dumps(self.autosets)
        }
        config["Presets"] = self.presets
        try:
            with io.StringIO() as string_stream:
                config.write(string_stream)
                content = string_stream.getvalue().strip()
            with open(self.file_path, "w") as file_handle: 
                file_handle.write(content)
            self.update_config_label()
            return True
        except Exception: 
            log_exception("save_config")
            return False

    def _save_preset_event(self, event=None):
        self.save_preset()

    def save_preset(self):
        name = self.preset_name_entry.get().strip()
        width = self.width_entry.get()
        height = self.height_entry.get()
        if name and width and height:
            self.presets[name] = f"{width},{height}"
            self.save_config()
            self.update_preset_list()
            self.preset_name_entry.delete(0, "end")
            self.preset_undo_stack.clear()
            self.preset_redo_stack.clear()
            self.last_preset_text = ""
            self.set_status(f"Preset '{name}' Saved", "#2ECC71")

    def load_preset_to_ui(self, name):
        if name in self.presets:
            width, height = self.presets[name].split(",")
            self.width_entry.delete(0, "end"); self.width_entry.insert(0, width)
            self.height_entry.delete(0, "end"); self.height_entry.insert(0, height)
            self.update_resolution_from_ui()
            self.set_status(f"Loaded '{name}'")

    def delete_preset(self, name):
        if name in self.presets:
            del self.presets[name]
            self.save_config()
            self.update_preset_list()
            self.set_status(f"Deleted '{name}'", "#E74C3C")

    def rename_preset(self, old_name):
        self.editing_inline = old_name
        self.update_preset_list()

    def update_preset_list(self, search_query=""):
        for widget in self.presets_frame.winfo_children(): 
            widget.destroy()
            
        for name, resolution in self.presets.items():
            if search_query and search_query.lower() not in name.lower():
                continue
                
            row_frame = ctk.CTkFrame(self.presets_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_columnconfigure(1, weight=0)
            
            if getattr(self, "editing_inline", None) == name:
                entry = ctk.CTkEntry(row_frame, height=28)
                entry.insert(0, name)
                entry.grid(row=0, column=0, sticky="we", padx=(0, 5))
                
                def save_inline(old=name, entry_widget=entry):
                    new_name = entry_widget.get().strip()
                    if new_name and new_name != old:
                        new_presets = {}
                        for key, value in self.presets.items():
                            if key == old: new_presets[new_name] = value
                            else: new_presets[key] = value
                        self.presets = new_presets
                        self.save_config()
                    self.editing_inline = None
                    self.update_preset_list(self.search_entry.get())
                    if new_name: self.set_status(f"Renamed to '{new_name}'", "#2ECC71")
                
                entry.bind("<Return>", lambda event, old=name, ent=entry: save_inline(old, ent))
                entry.bind("<Escape>", lambda event: [setattr(self, 'editing_inline', None), self.update_preset_list(self.search_entry.get())])
                ctk.CTkButton(row_frame, text="✓", width=28, height=28, fg_color="#2ECC71", hover_color="#27AE60", command=save_inline).grid(row=0, column=1)
                entry.focus_set()
                entry.select_range(0, 'end')
            else:
                name_button = ctk.CTkButton(row_frame, text=name, height=28, anchor="w", fg_color="#2C3E50", hover_color="#34495E", command=lambda n=name: self.load_preset_to_ui(n))
                name_button.grid(row=0, column=0, sticky="we", padx=(0, 5))
                
                resolution_button = ctk.CTkButton(row_frame, text=resolution, width=80, height=28, fg_color="#1F6AA5", hover_color="#144870", command=lambda n=name: self.load_preset_to_ui(n))
                resolution_button.grid(row=0, column=1, sticky="e")
                
                menu = ctk.CTkOptionMenu(self, values=["Rename", "Delete"], command=lambda value, n=name: self._menu_handler(value, n))
                name_button.bind("<Button-3>", lambda event, m=menu: m._dropdown_menu.tk_popup(event.x_root, event.y_root))
                resolution_button.bind("<Button-3>", lambda event, m=menu: m._dropdown_menu.tk_popup(event.x_root, event.y_root))

    def _menu_handler(self, value, name):
        if value == "Rename": self.rename_preset(name)
        elif value == "Delete": self.delete_preset(name)

    def set_status(self, text, color="gray", auto_reset=True):
        if self.status_timer: self.after_cancel(self.status_timer); self.status_timer = None
        self.status_label.configure(text=text, text_color=color)
        if auto_reset: self.status_timer = self.after(5000, lambda: self.status_label.configure(text="Ready", text_color="gray"))

    def toggle_always_on_top(self):
        is_on = self.topmost_checkbox.get()
        self.attributes("-topmost", is_on)
        self.always_on_top_val = is_on
        if self.width and self.height: self.save_config()

    def update_countdown_from_entry(self, *args):
        try:
            value = self.countdown_entry.get()
            if value == "": return
            self.countdown_val = int(value)
            if self.width and self.height: self.save_config()
        except ValueError: pass

    def parse_ratio(self):
        ratio_string = self.ratio_combobox.get().strip()
        if ratio_string in ("Free", "0", ""): return None
        parts = ratio_string.split(":") if ":" in ratio_string else ratio_string.split()
        if len(parts) == 2:
            try: 
                ratio_width, ratio_height = float(parts[0]), float(parts[1])
                if ratio_width == 0 or ratio_height == 0: return None
                return ratio_width, ratio_height
            except ValueError: return None
        return None

    def update_resolution_from_ui(self, event=None, trigger=None):
        try:
            parsed = self.parse_ratio()
            width, height = 0, 0
            if trigger == "width":
                width = int(self.width_entry.get() or 0)
                if parsed: height = int(width * parsed[1] / parsed[0]); self.height_entry.delete(0, "end"); self.height_entry.insert(0, str(height))
                else: height = int(self.height_entry.get() or 0)
            elif trigger == "height":
                height = int(self.height_entry.get() or 0)
                if parsed: width = int(height * parsed[0] / parsed[1]); self.width_entry.delete(0, "end"); self.width_entry.insert(0, str(width))
                else: width = int(self.width_entry.get() or 0)
            else:
                width = int(self.width_entry.get() or 0)
                height = int(self.height_entry.get() or 0)
            if width > 0 and height > 0:
                self.width, self.height = width, height
                self.save_config()
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
            previous = self.preset_undo_stack.pop()
            self.preset_name_entry.delete(0, "end")
            self.preset_name_entry.insert(0, previous)
            self.last_preset_text = previous
        return "break"

    def _redo_preset_text(self, event):
        if self.preset_redo_stack:
            self.preset_undo_stack.append(self.last_preset_text)
            next_text = self.preset_redo_stack.pop()
            self.preset_name_entry.delete(0, "end")
            self.preset_name_entry.insert(0, next_text)
            self.last_preset_text = next_text
        return "break"

    def setup_ui(self):
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.paned_window = tk.PanedWindow(main_container, orient="horizontal", bd=0, sashwidth=6, bg="#242424", sashcursor="sb_h_double_arrow", opaqueresize=True)
        self.paned_window.pack(fill="both", expand=True)
        
        self.paned_window.bind("<ButtonPress-1>", self.start_paned_resize)
        self.paned_window.bind("<ButtonRelease-1>", self.stop_paned_resize)
        
        self.column1 = ctk.CTkFrame(self.paned_window, width=self.column1_width)
        self.column2 = ctk.CTkFrame(self.paned_window, width=self.column2_width)
        self.column3 = ctk.CTkFrame(self.paned_window, width=self.column3_width)
        
        self.paned_window.add(self.column1, minsize=280)
        self.paned_window.paneconfig(self.column1, width=self.column1_width)
        
        self.paned_window.add(self.column2, minsize=280)
        self.paned_window.paneconfig(self.column2, width=self.column2_width)
        
        self.paned_window.add(self.column3, minsize=380)
        self.paned_window.paneconfig(self.column3, width=self.column3_width)
        
        self.column1.bind("<Configure>", lambda e: self.update_pane_labels())
        self.column2.bind("<Configure>", lambda e: self.update_pane_labels())
        self.column3.bind("<Configure>", lambda e: self.update_pane_labels())
        
        self.setup_column1()
        self.setup_column2()
        self.setup_column3()

    def update_pane_labels(self):
        if not hasattr(self, 'column1_width_label'): return
        
        column1_val = self.column1.winfo_width()
        column2_val = self.column2.winfo_width()
        column3_val = self.column3.winfo_width()
        
        active_widget = self.focus_get()
        
        if column1_val > 50 and column1_val != self.column1_width:
            self.column1_width = column1_val
            if active_widget != self.column1_width_label:
                self.column1_width_label.delete(0, "end")
                self.column1_width_label.insert(0, f"{column1_val}px")
                
        if column2_val > 50 and column2_val != self.column2_width:
            self.column2_width = column2_val
            if active_widget != self.column2_width_label:
                self.column2_width_label.delete(0, "end")
                self.column2_width_label.insert(0, f"{column2_val}px")
                
        if column3_val > 50 and column3_val != self.column3_width:
            self.column3_width = column3_val
            if active_widget != self.column3_width_label:
                self.column3_width_label.delete(0, "end")
                self.column3_width_label.insert(0, f"{column3_val}px")

    def apply_manual_pane_size(self, column_num):
        try:
            if column_num == 1:
                val_str = self.column1_width_label.get().lower().replace("px", "").strip()
                val = int(val_str)
                self.paned_window.paneconfig(self.column1, width=val)
                self.column1_width = val
                self.focus_set()
            elif column_num == 2:
                val_str = self.column2_width_label.get().lower().replace("px", "").strip()
                val = int(val_str)
                self.paned_window.paneconfig(self.column2, width=val)
                self.column2_width = val
                self.focus_set()
            elif column_num == 3:
                val_str = self.column3_width_label.get().lower().replace("px", "").strip()
                val = int(val_str)
                self.paned_window.paneconfig(self.column3, width=val)
                self.column3_width = val
                self.focus_set()
            
            self.save_config()
            self.update_pane_labels()
        except ValueError:
            self.update_pane_labels()

    def reset_pane_size(self, column_num):
        if column_num == 1:
            self.paned_window.paneconfig(self.column1, width=280)
        elif column_num == 2:
            self.paned_window.paneconfig(self.column2, width=280)
        elif column_num == 3:
            self.paned_window.paneconfig(self.column3, width=418)
        self.update_pane_labels()
        self.save_config()

    def setup_column1(self):
        monitor_info = win32api.GetMonitorInfo(win32api.MonitorFromPoint((0, 0)))
        work_area = monitor_info['Work']
        monitor_width, monitor_height = work_area[2] - work_area[0], work_area[3] - work_area[1]
        
        header_frame = ctk.CTkFrame(self.column1, fg_color="transparent")
        header_frame.pack(fill="x", padx=5, pady=5)
        
        left_header = ctk.CTkFrame(header_frame, fg_color="transparent")
        left_header.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(left_header, text="Current Display", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(left_header, text=f"{monitor_width}x{monitor_height}", font=ctk.CTkFont(size=13)).pack(anchor="w")
        
        right_header = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_header.pack(side="right")
        
        ctk.CTkButton(right_header, text="↺", width=28, height=28, fg_color="#34495E", hover_color="#2C3E50", command=lambda: self.reset_pane_size(1)).pack(side="right", padx=(5, 0))
        
        self.config_label = ctk.CTkLabel(right_header, text="", font=ctk.CTkFont(size=14, weight="bold"), text_color="#1F6AA5")
        self.config_label.pack(side="right")
        self.update_config_label()
        
        card_resolution = ctk.CTkFrame(self.column1, corner_radius=8)
        card_resolution.pack(fill="x", padx=5, pady=5)
        resolution_inner = ctk.CTkFrame(card_resolution, fg_color="transparent")
        resolution_inner.pack(padx=5, pady=5, fill="x")
        resolution_inner.grid_columnconfigure((0, 1, 2), weight=1)
        self.width_entry = ctk.CTkEntry(resolution_inner, placeholder_text="Width", height=28)
        self.width_entry.grid(row=0, column=0, padx=(0, 5), sticky="we")
        self.width_entry.insert(0, str(self.width)); self.width_entry.bind("<KeyRelease>", lambda event: self.update_resolution_from_ui(event, "width"))
        self.height_entry = ctk.CTkEntry(resolution_inner, placeholder_text="Height", height=28)
        self.height_entry.grid(row=0, column=1, padx=2, sticky="we")
        self.height_entry.insert(0, str(self.height)); self.height_entry.bind("<KeyRelease>", lambda event: self.update_resolution_from_ui(event, "height"))
        self.ratio_combobox = ctk.CTkComboBox(resolution_inner, values=["Free", "16:9", "4:3", "21:9"], height=28, command=lambda value: self.update_resolution_from_ui(None, "ratio"))
        self.ratio_combobox.grid(row=0, column=2, padx=(5, 0), sticky="we"); self.ratio_combobox.set("Free")

        control_frame = ctk.CTkFrame(self.column1, fg_color="transparent")
        control_frame.pack(fill="x", padx=5, pady=5)
        self.topmost_checkbox = ctk.CTkCheckBox(control_frame, text="Always On Top", font=ctk.CTkFont(size=13), command=self.toggle_always_on_top)
        self.topmost_checkbox.pack(side="left", padx=5)
        if self.always_on_top_val: self.topmost_checkbox.select()
        ctk.CTkLabel(control_frame, text="Delay (s):", font=ctk.CTkFont(size=13)).pack(side="left", padx=(10, 5))
        self.countdown_entry = ctk.CTkEntry(control_frame, width=45, height=26); self.countdown_entry.insert(0, str(self.countdown_val))
        self.countdown_entry.pack(side="left"); self.countdown_entry.bind("<KeyRelease>", self.update_countdown_from_entry)

        action_frame = ctk.CTkFrame(self.column1, fg_color="transparent")
        action_frame.pack(fill="x", padx=5, pady=5)
        action_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(action_frame, text="Capture Active", height=32, font=ctk.CTkFont(size=13, weight="bold"), fg_color="#1F6AA5", command=lambda: self.delayed_action(self.check_save)).grid(row=0, column=0, padx=2, pady=2, sticky="we")
        ctk.CTkButton(action_frame, text="Apply Active", height=32, font=ctk.CTkFont(size=13, weight="bold"), fg_color="#1F6AA5", command=lambda: self.delayed_action(self.resize_only)).grid(row=0, column=1, padx=2, pady=2, sticky="we")
        ctk.CTkButton(action_frame, text="Reload Config", height=28, command=self.reload_ui_config).grid(row=1, column=0, padx=2, pady=2, sticky="we")
        ctk.CTkButton(action_frame, text="Open Folder", height=28, command=self.open_folder).grid(row=1, column=1, padx=2, pady=2, sticky="we")

        self.focus_box = ctk.CTkTextbox(self.column1, height=32, corner_radius=6, fg_color="#2B2B2B", text_color="#2ECC71", font=ctk.CTkFont(size=12, weight="bold"))
        self.focus_box.pack(fill="x", padx=5, pady=5); self.focus_box.configure(state="disabled")

        position_frame = ctk.CTkFrame(self.column1, corner_radius=8, fg_color="#2B2B2B")
        position_frame.pack(pady=5) 
        symbols = [("↖", "1"), ("↑", "2"), ("↗", "3"), ("←", "4"), ("•", "5"), ("→", "6"), ("↙", "7"), ("↓", "8"), ("↘", "9")]
        for i, (symbol, command) in enumerate(symbols):
            row, col = divmod(i, 3)
            ctk.CTkButton(position_frame, text=symbol, width=46, height=46, font=ctk.CTkFont(size=20, weight="bold"), 
                          fg_color="#1F6AA5", corner_radius=6, 
                          command=lambda m=command: self.delayed_action(lambda: self.move_window(m))
                         ).grid(row=row, column=col, padx=4, pady=4)
                         
        footer1 = ctk.CTkFrame(self.column1, fg_color="transparent", height=20)
        footer1.pack(side="bottom", fill="x", padx=5, pady=2)
        self.status_label = ctk.CTkLabel(footer1, text="Ready", font=ctk.CTkFont(size=13, weight="bold"), text_color="gray")
        self.status_label.pack(side="left")
        
        self.column1_width_label = ctk.CTkEntry(footer1, width=65, height=22, font=ctk.CTkFont(size=11), text_color="gray", fg_color="transparent", border_width=1)
        self.column1_width_label.pack(side="right")
        self.column1_width_label.insert(0, f"{self.column1_width}px")
        self.column1_width_label.bind("<Return>", lambda e: self.apply_manual_pane_size(1))

    def setup_column2(self):
        header2 = ctk.CTkFrame(self.column2, fg_color="transparent")
        header2.pack(fill="x", padx=5, pady=(5, 2))
        ctk.CTkLabel(header2, text="Presets", font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
        ctk.CTkButton(header2, text="↺", width=28, height=28, fg_color="#34495E", hover_color="#2C3E50", command=lambda: self.reset_pane_size(2)).pack(side="right")
        
        search_frame = ctk.CTkFrame(self.column2, fg_color="transparent")
        search_frame.pack(fill="x", padx=5, pady=2)
        self.search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search Presets...", height=28)
        self.search_entry.pack(fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", lambda event: self.update_preset_list(self.search_entry.get()))
        
        preset_top = ctk.CTkFrame(self.column2, fg_color="transparent")
        preset_top.pack(fill="x", padx=5, pady=2)
        self.preset_name_entry = ctk.CTkEntry(preset_top, placeholder_text="New Preset...", height=28)
        self.preset_name_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.preset_name_entry.bind("<KeyRelease>", self._track_preset_text)
        self.preset_name_entry.bind("<Control-z>", self._undo_preset_text)
        self.preset_name_entry.bind("<Control-y>", self._redo_preset_text)
        self.preset_name_entry.bind("<Return>", self._save_preset_event)
        ctk.CTkButton(preset_top, text="Save", width=60, height=28, font=ctk.CTkFont(weight="bold"), command=self.save_preset).pack(side="right")
        
        self.presets_frame = ctk.CTkScrollableFrame(self.column2, fg_color="transparent")
        self.presets_frame.pack(fill="both", expand=True, padx=5, pady=(2, 5))
        self.update_preset_list()

        footer2 = ctk.CTkFrame(self.column2, fg_color="transparent", height=20)
        footer2.pack(side="bottom", fill="x", padx=5, pady=2)
        
        self.column2_width_label = ctk.CTkEntry(footer2, width=65, height=22, font=ctk.CTkFont(size=11), text_color="gray", fg_color="transparent", border_width=1)
        self.column2_width_label.pack(side="right")
        self.column2_width_label.insert(0, f"{self.column2_width}px")
        self.column2_width_label.bind("<Return>", lambda e: self.apply_manual_pane_size(2))

    def setup_column3(self):
        header3 = ctk.CTkFrame(self.column3, fg_color="transparent")
        header3.pack(fill="x", padx=5, pady=(5, 2))
        ctk.CTkLabel(header3, text="Automatic Profiles", font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
        ctk.CTkButton(header3, text="↺", width=28, height=28, fg_color="#34495E", hover_color="#2C3E50", command=lambda: self.reset_pane_size(3)).pack(side="right", padx=(5,0))
        ctk.CTkButton(header3, text="Add Rule", width=80, height=28, command=self.add_empty_autoset).pack(side="right", padx=(5,0))
        ctk.CTkButton(header3, text="Add Target", width=100, height=28, fg_color="#27AE60", hover_color="#2ECC71", command=lambda: self.delayed_action(self.add_current_autoset)).pack(side="right")

        self.autosets_frame = ctk.CTkScrollableFrame(self.column3, fg_color="transparent")
        self.autosets_frame.pack(fill="both", expand=True, padx=2, pady=2)
        self.render_autosets()
        
        footer3 = ctk.CTkFrame(self.column3, fg_color="transparent", height=20)
        footer3.pack(side="bottom", fill="x", padx=5, pady=2)
        
        self.column3_width_label = ctk.CTkEntry(footer3, width=65, height=22, font=ctk.CTkFont(size=11), text_color="gray", fg_color="transparent", border_width=1)
        self.column3_width_label.pack(side="right")
        self.column3_width_label.insert(0, f"{self.column3_width}px")
        self.column3_width_label.bind("<Return>", lambda e: self.apply_manual_pane_size(3))

    def add_empty_autoset(self):
        new_set = {"executable": "", "width": self.width, "height": self.height, "x_position": 0, "y_position": 0, "automatic_position": False, "automatic_size": False, "trigger": "On Focus"}
        self.autosets.append(new_set)
        self.save_config()
        self.render_autosets()

    def add_current_autoset(self):
        active_window = gw.getActiveWindow()
        if active_window and active_window.title != self.title():
            try:
                hwnd = active_window._hWnd
                _, process_id = win32process.GetWindowThreadProcessId(hwnd)
                executable_name = self.get_process_name_cached(process_id)
                
                left_offset, top_offset, right_offset, bottom_offset = self.get_window_offsets(hwnd)
                x_position = active_window.left + left_offset
                y_position = active_window.top + top_offset
                window_width = active_window.width - left_offset - right_offset
                window_height = active_window.height - top_offset - bottom_offset
                
                new_set = {"executable": executable_name, "width": window_width, "height": window_height, "x_position": x_position, "y_position": y_position, "automatic_position": True, "automatic_size": True, "trigger": "On Focus"}
                self.autosets.append(new_set)
                self.save_config()
                self.render_autosets()
                self.set_status(f"Added Automatic Set: {executable_name}", "#2ECC71")
            except Exception: 
                log_exception("add_current_autoset")
                self.set_status("Failed to add target", "#E74C3C")
        else: self.set_status("No valid target found", "#E74C3C")

    def move_autoset(self, index, direction):
        if direction == "up" and index > 0:
            self.autosets[index], self.autosets[index-1] = self.autosets[index-1], self.autosets[index]
        elif direction == "down" and index < len(self.autosets) - 1:
            self.autosets[index], self.autosets[index+1] = self.autosets[index+1], self.autosets[index]
        self.save_config()
        self.render_autosets()

    def remove_autoset(self, index):
        if 0 <= index < len(self.autosets):
            self.autosets.pop(index)
            self.save_config()
            self.render_autosets()

    def update_autoset_data(self, index, key, value):
        if 0 <= index < len(self.autosets):
            self.autosets[index][key] = value
            self.save_config()

    def render_autosets(self):
        for widget in self.autosets_frame.winfo_children(): widget.destroy()
        
        for index, autoset in enumerate(self.autosets):
            card = ctk.CTkFrame(self.autosets_frame, corner_radius=6, border_width=1, border_color="#34495E")
            card.pack(fill="x", pady=3, padx=2)
            
            row1 = ctk.CTkFrame(card, fg_color="transparent")
            row1.pack(fill="x", padx=5, pady=(5, 2))
            executable_entry = ctk.CTkEntry(row1, placeholder_text="Target Executable", height=26)
            executable_entry.pack(side="left", fill="x", expand=True)
            executable_entry.insert(0, autoset.get("executable", ""))
            executable_entry.bind("<FocusOut>", lambda event, i=index, widget=executable_entry: self.update_autoset_data(i, "executable", widget.get()))
            
            ctk.CTkButton(row1, text="↑", width=26, height=26, command=lambda i=index: self.move_autoset(i, "up")).pack(side="left", padx=(4,0))
            ctk.CTkButton(row1, text="↓", width=26, height=26, command=lambda i=index: self.move_autoset(i, "down")).pack(side="left", padx=(2,0))
            ctk.CTkButton(row1, text="X", width=26, height=26, fg_color="#E74C3C", hover_color="#C0392B", command=lambda i=index: self.remove_autoset(i)).pack(side="left", padx=(4,0))

            row2 = ctk.CTkFrame(card, fg_color="transparent")
            row2.pack(fill="x", padx=5, pady=2)
            
            size_checkbox = ctk.CTkCheckBox(row2, text="Auto Size", width=95, command=lambda i=index, widgets=locals(): self.update_autoset_data(i, "automatic_size", widgets['size_checkbox'].get()))
            size_checkbox.pack(side="left")
            if autoset.get("automatic_size", False): size_checkbox.select()
            
            width_entry = ctk.CTkEntry(row2, placeholder_text="Width", width=65, height=26)
            width_entry.pack(side="left", padx=2)
            width_entry.insert(0, str(autoset.get("width", 0)))
            width_entry.bind("<FocusOut>", lambda event, i=index, widget=width_entry: self.update_autoset_data(i, "width", int(widget.get() or 0)))
            
            height_entry = ctk.CTkEntry(row2, placeholder_text="Height", width=65, height=26)
            height_entry.pack(side="left", padx=2)
            height_entry.insert(0, str(autoset.get("height", 0)))
            height_entry.bind("<FocusOut>", lambda event, i=index, widget=height_entry: self.update_autoset_data(i, "height", int(widget.get() or 0)))

            trigger_combobox = ctk.CTkComboBox(row2, values=["On Focus", "Always"], height=26, command=lambda value, i=index: self.update_autoset_data(i, "trigger", value))
            trigger_combobox.pack(side="right")
            trigger_combobox.set(autoset.get("trigger", "On Focus"))

            row3 = ctk.CTkFrame(card, fg_color="transparent")
            row3.pack(fill="x", padx=5, pady=(2, 5))
            
            position_checkbox = ctk.CTkCheckBox(row3, text="Auto Position", width=95, command=lambda i=index, widgets=locals(): self.update_autoset_data(i, "automatic_position", widgets['position_checkbox'].get()))
            position_checkbox.pack(side="left")
            if autoset.get("automatic_position", False): position_checkbox.select()
            
            x_position_entry = ctk.CTkEntry(row3, placeholder_text="X Position", width=65, height=26)
            x_position_entry.pack(side="left", padx=2)
            x_position_entry.insert(0, str(autoset.get("x_position", 0)))
            x_position_entry.bind("<FocusOut>", lambda event, i=index, widget=x_position_entry: self.update_autoset_data(i, "x_position", int(widget.get() or 0)))
            
            y_position_entry = ctk.CTkEntry(row3, placeholder_text="Y Position", width=65, height=26)
            y_position_entry.pack(side="left", padx=2)
            y_position_entry.insert(0, str(autoset.get("y_position", 0)))
            y_position_entry.bind("<FocusOut>", lambda event, i=index, widget=y_position_entry: self.update_autoset_data(i, "y_position", int(widget.get() or 0)))

    def update_config_label(self):
        value = f"{self.width}x{self.height}" if self.width else "None"
        self.config_label.configure(text=f"[{value}]")

    def get_process_name_cached(self, process_id):
        try:
            process = psutil.Process(process_id)
            create_time = process.create_time()
            if process_id in self.pid_cache:
                cached_name, cached_time = self.pid_cache[process_id]
                if cached_time == create_time:
                    return cached_name
            
            name = process.name()
            self.pid_cache[process_id] = (name, create_time)
            return name
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return ""

    def get_active_process_name(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, process_id = win32process.GetWindowThreadProcessId(hwnd)
            return self.get_process_name_cached(process_id)
        except: return "Unknown"

    def update_focus_display(self, executable_name):
        self.focus_box.configure(state="normal")
        self.focus_box.delete("1.0", "end")
        self.focus_box.insert("1.0", f"> {executable_name}")
        self.focus_box.configure(state="disabled")
        
    def open_folder(self):
        os.startfile(os.path.dirname(os.path.abspath(__file__)))

    def start_focus_tracker(self):
        def track():
            while True:
                if getattr(self, "is_resizing", False):
                    time.sleep(0.3)
                    continue
                try:
                    executable = self.get_active_process_name()
                    self.after(0, lambda e=executable: self.update_focus_display(e))
                except Exception: pass
                time.sleep(0.5)
        threading.Thread(target=track, daemon=True).start()

    def get_window_offsets(self, hwnd):
        try:
            win_rect = wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(win_rect))
            
            dwm_rect = wintypes.RECT()
            ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(dwm_rect), ctypes.sizeof(dwm_rect))
            
            left_offset = dwm_rect.left - win_rect.left
            top_offset = dwm_rect.top - win_rect.top
            right_offset = win_rect.right - dwm_rect.right
            bottom_offset = win_rect.bottom - dwm_rect.bottom
            
            return left_offset, top_offset, right_offset, bottom_offset
        except Exception:
            return 0, 0, 0, 0

    def start_auto_enforcer(self):
        def enforcer_loop():
            last_focus = 0
            while True:
                time.sleep(0.5)
                if not self.autosets:
                    continue
                if getattr(self, "is_resizing", False):
                    continue
                
                try:
                    current_active = win32gui.GetForegroundWindow()
                    
                    has_always_trigger = any(rule.get("trigger") == "Always" for rule in self.autosets)
                    hwnds = []
                    
                    if has_always_trigger:
                        def enumerate_callback(hwnd, result):
                            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                                result.append(hwnd)
                        win32gui.EnumWindows(enumerate_callback, hwnds)
                    else:
                        if current_active and current_active != 0:
                            hwnds = [current_active]
                    
                    for hwnd in hwnds:
                        try:
                            _, process_id = win32process.GetWindowThreadProcessId(hwnd)
                            executable_name = self.get_process_name_cached(process_id)
                            if not executable_name: continue
                        except: continue

                        is_minimized = win32gui.IsIconic(hwnd)
                        is_focused = (hwnd == current_active)
                        was_focused = (hwnd == last_focus)

                        for rule in self.autosets:
                            rule_executable = rule.get("executable", "").strip()
                            if not rule_executable or executable_name.lower() != rule_executable.lower():
                                continue
                                
                            trigger_mode = rule.get("trigger", "On Focus")
                            do_enforce = False
                            
                            if trigger_mode == "Always" and not is_minimized:
                                do_enforce = True
                            elif trigger_mode == "On Focus" and is_focused and not was_focused:
                                do_enforce = True
                                
                            if do_enforce:
                                try:
                                    win_rect = wintypes.RECT()
                                    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(win_rect))
                                    
                                    left_offset, top_offset, right_offset, bottom_offset = self.get_window_offsets(hwnd)
                                    
                                    needs_move = False
                                    needs_resize = False
                                    
                                    current_x = win_rect.left + left_offset
                                    current_y = win_rect.top + top_offset
                                    current_width = (win_rect.right - win_rect.left) - left_offset - right_offset
                                    current_height = (win_rect.bottom - win_rect.top) - top_offset - bottom_offset
                                    
                                    if rule.get("automatic_position", False):
                                        if current_x != rule.get("x_position", 0) or current_y != rule.get("y_position", 0):
                                            needs_move = True
                                            
                                    if rule.get("automatic_size", False):
                                        if current_width != rule.get("width", 0) or current_height != rule.get("height", 0):
                                            needs_resize = True

                                    if needs_move or needs_resize:
                                        new_x = rule.get("x_position", current_x) if needs_move else current_x
                                        new_y = rule.get("y_position", current_y) if needs_move else current_y
                                        new_width = rule.get("width", current_width) if needs_resize else current_width
                                        new_height = rule.get("height", current_height) if needs_resize else current_height
                                        
                                        final_x = new_x - left_offset
                                        final_y = new_y - top_offset
                                        final_width = new_width + left_offset + right_offset
                                        final_height = new_height + top_offset + bottom_offset
                                        
                                        flags = 0x0004 | 0x0010 
                                        if not needs_move: flags |= 0x0002
                                        if not needs_resize: flags |= 0x0001
                                        win32gui.SetWindowPos(hwnd, 0, final_x, final_y, final_width, final_height, flags)
                                except Exception:
                                    log_exception("enforcer")
                    last_focus = current_active
                except Exception:
                    pass
        threading.Thread(target=enforcer_loop, daemon=True).start()

    def delayed_action(self, function):
        def wrapper():
            for index in range(self.countdown_val, 0, -1):
                self.set_status(f"Action in {index}s...", "#F39C12", auto_reset=False)
                time.sleep(1)
            self.after(0, function)
        threading.Thread(target=wrapper, daemon=True).start()

    def check_save(self):
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            win_rect = wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(win_rect))
            left_offset, top_offset, right_offset, bottom_offset = self.get_window_offsets(hwnd)
            window_width = (win_rect.right - win_rect.left) - left_offset - right_offset
            window_height = (win_rect.bottom - win_rect.top) - top_offset - bottom_offset
            self.width_entry.delete(0, "end")
            self.width_entry.insert(0, str(window_width))
            self.height_entry.delete(0, "end")
            self.height_entry.insert(0, str(window_height))
            self.update_resolution_from_ui()
            self.set_status("Captured active window size", "#2ECC71")

    def resize_only(self):
        hwnd = win32gui.GetForegroundWindow()
        if hwnd and self.width and self.height:
            left_offset, top_offset, right_offset, bottom_offset = self.get_window_offsets(hwnd)
            final_width = self.width + left_offset + right_offset
            final_height = self.height + top_offset + bottom_offset
            win32gui.SetWindowPos(hwnd, 0, 0, 0, final_width, final_height, 0x0002 | 0x0004 | 0x0010)
            self.set_status("Resized active window", "#2ECC71")

    def reload_ui_config(self):
        self.width, self.height, self.always_on_top_val, self.countdown_val, self.column1_width, self.column2_width, self.column3_width = self.load_config()
        self.width_entry.delete(0, "end")
        self.width_entry.insert(0, str(self.width))
        self.height_entry.delete(0, "end")
        self.height_entry.insert(0, str(self.height))
        self.countdown_entry.delete(0, "end")
        self.countdown_entry.insert(0, str(self.countdown_val))
        
        self.paned_window.paneconfig(self.column1, width=self.column1_width)
        self.paned_window.paneconfig(self.column2, width=self.column2_width)
        self.paned_window.paneconfig(self.column3, width=self.column3_width)
        self.update_pane_labels()
        
        if self.always_on_top_val:
            self.topmost_checkbox.select()
        else:
            self.topmost_checkbox.deselect()
            
        self.update_config_label()
        self.update_preset_list()
        self.render_autosets()
        self.set_status("Configuration Reloaded", "#3498DB")

    def move_window(self, position):
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd: return
        
        monitor_info = win32api.GetMonitorInfo(win32api.MonitorFromWindow(hwnd))
        work_area = monitor_info['Work']
        monitor_width, monitor_height = work_area[2] - work_area[0], work_area[3] - work_area[1]
        monitor_x, monitor_y = work_area[0], work_area[1]
        
        win_rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(win_rect))
        
        left_offset, top_offset, right_offset, bottom_offset = self.get_window_offsets(hwnd)
        current_width = (win_rect.right - win_rect.left) - left_offset - right_offset
        current_height = (win_rect.bottom - win_rect.top) - top_offset - bottom_offset
        
        new_x, new_y = monitor_x, monitor_y
        
        if position in ("1", "4", "7"): new_x = monitor_x
        elif position in ("2", "5", "8"): new_x = monitor_x + (monitor_width - current_width) // 2
        elif position in ("3", "6", "9"): new_x = monitor_x + monitor_width - current_width
        
        if position in ("1", "2", "3"): new_y = monitor_y
        elif position in ("4", "5", "6"): new_y = monitor_y + (monitor_height - current_height) // 2
        elif position in ("7", "8", "9"): new_y = monitor_y + monitor_height - current_height
        
        final_x = new_x - left_offset
        final_y = new_y - top_offset
        final_width = current_width + left_offset + right_offset
        final_height = current_height + top_offset + bottom_offset
        
        win32gui.SetWindowPos(hwnd, 0, final_x, final_y, final_width, final_height, 0x0004 | 0x0010)
        self.set_status(f"Moved Window to position {position}", "#2ECC71")

if __name__ == "__main__":
    app = WindowManagerGUI()
    app.mainloop()
