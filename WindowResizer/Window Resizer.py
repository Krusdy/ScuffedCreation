import sys
import os
import ctypes
import importlib.util

def is_administrator():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

if __name__ == "__main__":
    if not is_administrator():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{os.path.abspath(__file__)}"', None, 1)
        sys.exit()

import subprocess
import traceback

try:
    def ensure_dependencies():
        core_packages = ["pip", "setuptools", "wheel"]
        required_packages = ["customtkinter", "pygetwindow", "psutil", "pywin32", "pyperclip", "packaging", "darkdetect", "pystray", "Pillow"]
        all_packages = core_packages + required_packages
        import_mapping = {
            "pip": "pip",
            "setuptools": "setuptools",
            "wheel": "wheel",
            "customtkinter": "customtkinter",
            "pygetwindow": "pygetwindow",
            "psutil": "psutil",
            "pywin32": "win32gui",
            "pyperclip": "pyperclip",
            "packaging": "packaging",
            "darkdetect": "darkdetect",
            "pystray": "pystray",
            "Pillow": "PIL"
        }
        missing = []
        for package in all_packages:
            import_name = import_mapping.get(package, package)
            if importlib.util.find_spec(import_name) is None:
                missing.append(package)
        
        if missing:
            install_command = f"{sys.executable} -m pip install --upgrade " + " ".join(missing)
            print("Missing core or required libraries detected:")
            for package in missing:
                print(f"- {package}")
            print("\nRun the following command to install all missing libraries at once:")
            print(install_command)
            print("\nAttempting automatic installation and upgrade...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade"] + missing, check=True)
            except Exception as error_detail:
                print(f"Automatic installation failed: {error_detail}")
                input("Press Enter to exit...")
                sys.exit(1)

    ensure_dependencies()

    import customtkinter
    import tkinter
    import time
    import threading
    import pygetwindow
    import psutil
    import win32process
    import win32gui
    import win32api
    import win32console
    from ctypes import wintypes
    import configparser
    import io
    import json
    import logging
    import pyperclip
    import pystray
    from PIL import Image, ImageDraw, ImageTk

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
        except Exception:
            pass

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    class WindowManagerGUI(customtkinter.CTk):
        def __init__(self):
            super().__init__()
            self.title("Window Workspace")
            
            application_width = 1002
            application_height = 664
            
            self.update_idletasks()
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            horizontal_position = int((screen_width / 2) - (application_width / 2))
            vertical_position = int((screen_height / 2) - (application_height / 2))
            self.geometry(f"{application_width}x{application_height}+{horizontal_position}+{vertical_position}")
            self.resizable(True, True)
            self.minsize(1002, 664)
            
            self.file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
            self.presets = {}
            self.autosets = []
            self.is_resizing = False
            self.resize_timer = None
            self.width, self.height, self.always_on_top_value, self.countdown_value, self.column1_width, self.column2_width, self.column3_width = self.load_config()
            
            self.pending_resize = False
            self.status_timer = None
            self.preset_undo_stack = []
            self.preset_redo_stack = []
            self.last_preset_text = ""
            self.editing_inline = None
            
            self.process_identifier_cache = {} 
            self.tray_icon = None
            
            self.setup_application_icon()

            if self.always_on_top_value:
                self.attributes("-topmost", True)
                
            self.bind_class("Entry", "<Control-BackSpace>", self._control_backspace)
            self.bind("<Control-s>", self._save_preset_event)
            self.bind("<Configure>", self._on_window_configure)
            self.protocol("WM_DELETE_WINDOW", self.exit_from_tray)
            
            self.setup_user_interface()
            self.start_focus_tracker()
            self.start_automatic_enforcer()

        def create_app_icon(self):
            image = Image.new("RGB", (64, 64), color=(33, 150, 243))
            draw = ImageDraw.Draw(image)
            draw.rectangle((16, 16, 48, 48), fill=(255, 255, 255))
            draw.rectangle((24, 24, 40, 40), fill=(33, 150, 243))
            return image

        def setup_application_icon(self):
            try:
                icon_image = self.create_app_icon()
                self.app_icon_photo = ImageTk.PhotoImage(icon_image)
                self.iconphoto(True, self.app_icon_photo)
            except Exception:
                pass

        def _on_window_configure(self, event):
            if event.widget == self:
                self.is_resizing = True
                if self.resize_timer:
                    self.after_cancel(self.resize_timer)
                self.resize_timer = self.after(300, self.stop_window_resize)

        def stop_window_resize(self):
            self.is_resizing = False

        def start_paned_resize(self, event):
            try:
                if self.paned_window.sash_coord(0):
                    pass
            except Exception:
                pass
            self.is_resizing = True

        def stop_paned_resize(self, event):
            self.is_resizing = False
            self.save_config()

        def _control_backspace(self, event):
            widget = event.widget
            try:
                if widget.select_present():
                    widget.delete("sel.first", "sel.last")
                else:
                    index = widget.index("insert")
                    text = widget.get()[:index].rstrip()
                    delete_index = text.rfind(" ") + 1 if " " in text else 0
                    widget.delete(delete_index, index)
                return "break"
            except Exception:
                pass

        def load_config(self):
            configuration = configparser.ConfigParser()
            configuration.optionxform = str
            if not os.path.exists(self.file_path):
                return 1920, 1080, False, 3, 280, 280, 418
            try:
                configuration.read(self.file_path)
                width = int(configuration.get("Settings", "Width", fallback=1920))
                height = int(configuration.get("Settings", "Height", fallback=1080))
                always_on_top = configuration.getboolean("Settings", "AlwaysOnTop", fallback=False)
                countdown = int(configuration.get("Settings", "Countdown", fallback=3))
                column1_value = int(configuration.get("Settings", "Column1Width", fallback=280))
                column2_value = int(configuration.get("Settings", "Column2Width", fallback=280))
                column3_value = int(configuration.get("Settings", "Column3Width", fallback=418))
                
                autosets_string = configuration.get("Settings", "AutoSets", fallback="[]")
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
                            "trigger": rule.get("trigger", "On Focus"),
                            "filter_mode": rule.get("filter_mode", "Match"),
                            "whitelist_filters": rule.get("whitelist_filters", rule.get("title_filters", "")),
                            "blacklist_filters": rule.get("blacklist_filters", "")
                        })
                except Exception:
                    self.autosets = []
                    
                if configuration.has_section("Presets"):
                    self.presets = dict(configuration.items("Presets"))
                return width, height, always_on_top, countdown, column1_value, column2_value, column3_value
            except Exception:
                return 1920, 1080, False, 3, 280, 280, 418

        def save_config(self):
            configuration = configparser.ConfigParser()
            configuration.optionxform = str
            configuration["Settings"] = {
                "Width": str(self.width),
                "Height": str(self.height),
                "AlwaysOnTop": str(self.always_on_top_value),
                "Countdown": str(self.countdown_value),
                "Column1Width": str(self.column1_width),
                "Column2Width": str(self.column2_width),
                "Column3Width": str(self.column3_width),
                "AutoSets": json.dumps(self.autosets)
            }
            configuration["Presets"] = self.presets
            try:
                with io.StringIO() as string_stream:
                    configuration.write(string_stream)
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

        def load_preset_to_user_interface(self, name):
            if name in self.presets:
                width, height = self.presets[name].split(",")
                self.width_entry.delete(0, "end")
                self.width_entry.insert(0, width)
                self.height_entry.delete(0, "end")
                self.height_entry.insert(0, height)
                self.update_resolution_from_user_interface()
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
                    
                row_frame = customtkinter.CTkFrame(self.presets_frame, fg_color="transparent")
                row_frame.pack(fill="x", pady=2)
                row_frame.grid_columnconfigure(0, weight=1)
                row_frame.grid_columnconfigure(1, weight=0)
                
                if getattr(self, "editing_inline", None) == name:
                    entry = customtkinter.CTkEntry(row_frame, height=28)
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
                    
                    entry.bind("<Return>", lambda event, old=name, input_entity=entry: save_inline(old, input_entity))
                    entry.bind("<Escape>", lambda event: [setattr(self, 'editing_inline', None), self.update_preset_list(self.search_entry.get())])
                    customtkinter.CTkButton(row_frame, text="✓", width=28, height=28, fg_color="#2ECC71", hover_color="#27AE60", command=save_inline).grid(row=0, column=1)
                    entry.focus_set()
                    entry.select_range(0, 'end')
                else:
                    name_button = customtkinter.CTkButton(row_frame, text=name, height=28, anchor="w", fg_color="#2C3E50", hover_color="#34495E", command=lambda current_name=name: self.load_preset_to_user_interface(current_name))
                    name_button.grid(row=0, column=0, sticky="we", padx=(0, 5))
                    
                    resolution_button = customtkinter.CTkButton(row_frame, text=resolution, width=80, height=28, fg_color="#1F6AA5", hover_color="#144870", command=lambda current_name=name: self.load_preset_to_user_interface(current_name))
                    resolution_button.grid(row=0, column=1, sticky="e")
                    
                    menu = customtkinter.CTkOptionMenu(self, values=["Rename", "Delete"], command=lambda value, current_name=name: self._menu_handler(value, current_name))
                    name_button.bind("<Button-3>", lambda event, current_menu=menu: current_menu._dropdown_menu.tk_popup(event.x_root, event.y_root))
                    resolution_button.bind("<Button-3>", lambda event, current_menu=menu: current_menu._dropdown_menu.tk_popup(event.x_root, event.y_root))

        def _menu_handler(self, value, name):
            if value == "Rename": 
                self.rename_preset(name)
            elif value == "Delete": 
                self.delete_preset(name)

        def set_status(self, text, color="gray", auto_reset=True):
            if self.status_timer: 
                self.after_cancel(self.status_timer)
                self.status_timer = None
            self.status_label.configure(text=text, text_color=color)
            if auto_reset: 
                self.status_timer = self.after(5000, lambda: self.status_label.configure(text="Ready", text_color="gray"))

        def toggle_always_on_top(self):
            is_enabled = self.topmost_checkbox.get()
            self.attributes("-topmost", is_enabled)
            self.always_on_top_value = is_enabled
            if self.width and self.height: 
                self.save_config()

        def update_countdown_from_entry(self, *arguments):
            try:
                value = self.countdown_entry.get()
                if value == "": 
                    return
                self.countdown_value = int(value)
                if self.width and self.height: 
                    self.save_config()
            except ValueError: 
                pass

        def parse_ratio(self):
            ratio_string = self.ratio_combobox.get().strip()
            if ratio_string in ("Free", "0", ""): 
                return None
            parts = ratio_string.split(":") if ":" in ratio_string else ratio_string.split()
            if len(parts) == 2:
                try: 
                    ratio_width, ratio_height = float(parts[0]), float(parts[1])
                    if ratio_width == 0 or ratio_height == 0: 
                        return None
                    return ratio_width, ratio_height
                except ValueError: 
                    return None
            return None

        def update_resolution_from_user_interface(self, event=None, trigger=None):
            try:
                parsed = self.parse_ratio()
                width, height = 0, 0
                if trigger == "width":
                    width = int(self.width_entry.get() or 0)
                    if parsed: 
                        height = int(width * parsed[1] / parsed[0])
                        self.height_entry.delete(0, "end")
                        self.height_entry.insert(0, str(height))
                    else: 
                        height = int(self.height_entry.get() or 0)
                elif trigger == "height":
                    height = int(self.height_entry.get() or 0)
                    if parsed: 
                        width = int(height * parsed[0] / parsed[1])
                        self.width_entry.delete(0, "end")
                        self.width_entry.insert(0, str(width))
                    else: 
                        width = int(self.width_entry.get() or 0)
                else:
                    width = int(self.width_entry.get() or 0)
                    height = int(self.height_entry.get() or 0)
                if width > 0 and height > 0:
                    self.width, self.height = width, height
                    self.save_config()
            except ValueError: 
                pass

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

        def setup_user_interface(self):
            main_container = customtkinter.CTkFrame(self, fg_color="transparent")
            main_container.pack(fill="both", expand=True, padx=5, pady=5)
            
            self.paned_window = tkinter.PanedWindow(main_container, orient="horizontal", bd=0, sashwidth=6, bg="#242424", opaqueresize=True)
            self.paned_window.pack(fill="both", expand=True)
            
            self.paned_window.bind("<ButtonPress-1>", self.start_paned_resize)
            self.paned_window.bind("<ButtonRelease-1>", self.stop_paned_resize)
            
            self.column1 = customtkinter.CTkFrame(self.paned_window, width=self.column1_width)
            self.column2 = customtkinter.CTkFrame(self.paned_window, width=self.column2_width)
            self.column3 = customtkinter.CTkFrame(self.paned_window, width=self.column3_width)
            
            self.paned_window.add(self.column1, minsize=280)
            self.paned_window.paneconfig(self.column1, width=self.column1_width)
            
            self.paned_window.add(self.column2, minsize=280)
            self.paned_window.paneconfig(self.column2, width=self.column2_width)
            
            self.paned_window.add(self.column3, minsize=380)
            self.paned_window.paneconfig(self.column3, width=self.column3_width)
            
            self.column1.bind("<Configure>", lambda event: self.update_pane_labels())
            self.column2.bind("<Configure>", lambda event: self.update_pane_labels())
            self.column3.bind("<Configure>", lambda event: self.update_pane_labels())
            
            self.setup_column1()
            self.setup_column2()
            self.setup_column3()

        def update_pane_labels(self):
            if not hasattr(self, 'column1_width_label'): 
                return
            
            column1_value = self.column1.winfo_width()
            column2_value = self.column2.winfo_width()
            column3_value = self.column3.winfo_width()
            
            active_widget = self.focus_get()
            
            if column1_value > 50 and column1_value != self.column1_width:
                self.column1_width = column1_value
                if active_widget != self.column1_width_label:
                    self.column1_width_label.delete(0, "end")
                    self.column1_width_label.insert(0, f"{column1_value} pixels")
                    
            if column2_value > 50 and column2_value != self.column2_width:
                self.column2_width = column2_value
                if active_widget != self.column2_width_label:
                    self.column2_width_label.delete(0, "end")
                    self.column2_width_label.insert(0, f"{column2_value} pixels")
                    
            if column3_value > 50 and column3_value != self.column3_width:
                self.column3_width = column3_value
                if active_widget != self.column3_width_label:
                    self.column3_width_label.delete(0, "end")
                    self.column3_width_label.insert(0, f"{column3_value} pixels")

        def apply_manual_pane_size(self, column_number):
            try:
                if column_number == 1:
                    value_string = self.column1_width_label.get().lower().replace("pixels", "").strip()
                    value = int(value_string)
                    self.paned_window.paneconfig(self.column1, width=value)
                    self.column1_width = value
                    self.focus_set()
                elif column_number == 2:
                    value_string = self.column2_width_label.get().lower().replace("pixels", "").strip()
                    value = int(value_string)
                    self.paned_window.paneconfig(self.column2, width=value)
                    self.column2_width = value
                    self.focus_set()
                elif column_number == 3:
                    value_string = self.column3_width_label.get().lower().replace("pixels", "").strip()
                    value = int(value_string)
                    self.paned_window.paneconfig(self.column3, width=value)
                    self.column3_width = value
                    self.focus_set()
                
                self.save_config()
                self.update_pane_labels()
            except ValueError:
                self.update_pane_labels()

        def reset_pane_size(self, column_number):
            if column_number == 1:
                self.paned_window.paneconfig(self.column1, width=280)
            elif column_number == 2:
                self.paned_window.paneconfig(self.column2, width=280)
            elif column_number == 3:
                self.paned_window.paneconfig(self.column3, width=418)
            self.update_pane_labels()
            self.save_config()

        def setup_column1(self):
            monitor_information = win32api.GetMonitorInfo(win32api.MonitorFromPoint((0, 0)))
            work_area = monitor_information['Work']
            monitor_width, monitor_height = work_area[2] - work_area[0], work_area[3] - work_area[1]
            
            header_frame = customtkinter.CTkFrame(self.column1, fg_color="transparent")
            header_frame.pack(fill="x", padx=5, pady=5)
            
            left_header = customtkinter.CTkFrame(header_frame, fg_color="transparent")
            left_header.pack(side="left", fill="x", expand=True)
            customtkinter.CTkLabel(left_header, text="Current Display", font=customtkinter.CTkFont(size=14, weight="bold")).pack(anchor="w")
            customtkinter.CTkLabel(left_header, text=f"{monitor_width}x{monitor_height}", font=customtkinter.CTkFont(size=13)).pack(anchor="w")
            
            right_header = customtkinter.CTkFrame(header_frame, fg_color="transparent")
            right_header.pack(side="right")
            
            customtkinter.CTkButton(right_header, text="↺", width=28, height=28, fg_color="#34495E", hover_color="#2C3E50", command=lambda: self.reset_pane_size(1)).pack(side="right", padx=(5, 0))
            
            self.config_label = customtkinter.CTkLabel(right_header, text="", font=customtkinter.CTkFont(size=14, weight="bold"), text_color="#1F6AA5")
            self.config_label.pack(side="right")
            self.update_config_label()
            
            card_resolution = customtkinter.CTkFrame(self.column1, corner_radius=8)
            card_resolution.pack(fill="x", padx=5, pady=5)
            resolution_inner = customtkinter.CTkFrame(card_resolution, fg_color="transparent")
            resolution_inner.pack(padx=5, pady=5, fill="x")
            resolution_inner.grid_columnconfigure((0, 1, 2), weight=1)
            self.width_entry = customtkinter.CTkEntry(resolution_inner, placeholder_text="Width", height=28)
            self.width_entry.grid(row=0, column=0, padx=(0, 5), sticky="we")
            self.width_entry.insert(0, str(self.width))
            self.width_entry.bind("<KeyRelease>", lambda event: self.update_resolution_from_user_interface(event, "width"))
            self.height_entry = customtkinter.CTkEntry(resolution_inner, placeholder_text="Height", height=28)
            self.height_entry.grid(row=0, column=1, padx=2, sticky="we")
            self.height_entry.insert(0, str(self.height))
            self.height_entry.bind("<KeyRelease>", lambda event: self.update_resolution_from_user_interface(event, "height"))
            self.ratio_combobox = customtkinter.CTkComboBox(resolution_inner, values=["Free", "16:9", "4:3", "21:9"], height=28, command=lambda value: self.update_resolution_from_user_interface(None, "ratio"))
            self.ratio_combobox.grid(row=0, column=2, padx=(5, 0), sticky="we")
            self.ratio_combobox.set("Free")

            control_frame = customtkinter.CTkFrame(self.column1, fg_color="transparent")
            control_frame.pack(fill="x", padx=5, pady=5)
            self.topmost_checkbox = customtkinter.CTkCheckBox(control_frame, text="Always On Top", font=customtkinter.CTkFont(size=13), command=self.toggle_always_on_top)
            self.topmost_checkbox.pack(side="left", padx=5)
            if self.always_on_top_value: 
                self.topmost_checkbox.select()
            customtkinter.CTkLabel(control_frame, text="Delay (seconds):", font=customtkinter.CTkFont(size=13)).pack(side="left", padx=(10, 5))
            self.countdown_entry = customtkinter.CTkEntry(control_frame, width=45, height=26)
            self.countdown_entry.insert(0, str(self.countdown_value))
            self.countdown_entry.pack(side="left")
            self.countdown_entry.bind("<KeyRelease>", self.update_countdown_from_entry)

            action_frame = customtkinter.CTkFrame(self.column1, fg_color="transparent")
            action_frame.pack(fill="x", padx=5, pady=5)
            action_frame.grid_columnconfigure((0, 1), weight=1)
            customtkinter.CTkButton(action_frame, text="Capture Active", height=32, font=customtkinter.CTkFont(size=13, weight="bold"), fg_color="#1F6AA5", command=lambda: self.delayed_action(self.check_save)).grid(row=0, column=0, padx=2, pady=2, sticky="we")
            customtkinter.CTkButton(action_frame, text="Apply Active", height=32, font=customtkinter.CTkFont(size=13, weight="bold"), fg_color="#1F6AA5", command=lambda: self.delayed_action(self.resize_only)).grid(row=0, column=1, padx=2, pady=2, sticky="we")
            customtkinter.CTkButton(action_frame, text="Reload Config", height=28, command=self.reload_user_interface_config).grid(row=1, column=0, padx=2, pady=2, sticky="we")
            customtkinter.CTkButton(action_frame, text="Open Folder", height=28, command=self.open_folder).grid(row=1, column=1, padx=2, pady=2, sticky="we")

            tray_action_frame = customtkinter.CTkFrame(self.column1, fg_color="transparent")
            tray_action_frame.pack(fill="x", padx=5, pady=2)
            customtkinter.CTkButton(tray_action_frame, text="Minimize to Tray", height=28, fg_color="#2C3E50", hover_color="#34495E", command=self.hide_to_tray).pack(fill="x", expand=True)

            self.focus_box = customtkinter.CTkTextbox(self.column1, height=32, corner_radius=6, fg_color="#2B2B2B", text_color="#2ECC71", font=customtkinter.CTkFont(size=12, weight="bold"))
            self.focus_box.pack(fill="x", padx=5, pady=5)
            self.focus_box.configure(state="disabled")

            position_frame = customtkinter.CTkFrame(self.column1, corner_radius=8, fg_color="#2B2B2B")
            position_frame.pack(pady=5, padx=5) 
            symbols = [("↖", "1"), ("↑", "2"), ("↗", "3"), ("←", "4"), ("•", "5"), ("→", "6"), ("↙", "7"), ("↓", "8"), ("↘", "9")]
            for index, (symbol, command) in enumerate(symbols):
                row, column = divmod(index, 3)
                customtkinter.CTkButton(position_frame, text=symbol, width=46, height=46, font=customtkinter.CTkFont(size=20, weight="bold"), 
                              fg_color="#1F6AA5", corner_radius=6, 
                              command=lambda current_command=command: self.delayed_action(lambda: self.move_window(current_command))
                             ).grid(row=row, column=column, padx=4, pady=4)
                             
            footer1 = customtkinter.CTkFrame(self.column1, fg_color="transparent", height=20)
            footer1.pack(side="bottom", fill="x", padx=5, pady=2)
            self.status_label = customtkinter.CTkLabel(footer1, text="Ready", font=customtkinter.CTkFont(size=13, weight="bold"), text_color="gray")
            self.status_label.pack(side="left")
            
            self.column1_width_label = customtkinter.CTkEntry(footer1, width=85, height=22, font=customtkinter.CTkFont(size=11), text_color="gray", fg_color="transparent", border_width=1)
            self.column1_width_label.pack(side="right")
            self.column1_width_label.insert(0, f"{self.column1_width} pixels")
            self.column1_width_label.bind("<Return>", lambda event: self.apply_manual_pane_size(1))

        def setup_column2(self):
            header2 = customtkinter.CTkFrame(self.column2, fg_color="transparent")
            header2.pack(fill="x", padx=5, pady=(5, 2))
            customtkinter.CTkLabel(header2, text="Presets", font=customtkinter.CTkFont(size=15, weight="bold")).pack(side="left")
            customtkinter.CTkButton(header2, text="↺", width=28, height=28, fg_color="#34495E", hover_color="#2C3E50", command=lambda: self.reset_pane_size(2)).pack(side="right")
            
            search_frame = customtkinter.CTkFrame(self.column2, fg_color="transparent")
            search_frame.pack(fill="x", padx=5, pady=2)
            self.search_entry = customtkinter.CTkEntry(search_frame, placeholder_text="Search Presets...", height=28)
            self.search_entry.pack(fill="x", expand=True)
            self.search_entry.bind("<KeyRelease>", lambda event: self.update_preset_list(self.search_entry.get()))
            
            preset_top = customtkinter.CTkFrame(self.column2, fg_color="transparent")
            preset_top.pack(fill="x", padx=5, pady=2)
            self.preset_name_entry = customtkinter.CTkEntry(preset_top, placeholder_text="New Preset...", height=28)
            self.preset_name_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
            self.preset_name_entry.bind("<KeyRelease>", self._track_preset_text)
            self.preset_name_entry.bind("<Control-z>", self._undo_preset_text)
            self.preset_name_entry.bind("<Control-y>", self._redo_preset_text)
            self.preset_name_entry.bind("<Return>", self._save_preset_event)
            customtkinter.CTkButton(preset_top, text="Save", width=60, height=28, font=customtkinter.CTkFont(weight="bold"), command=self.save_preset).pack(side="right")
            
            self.presets_frame = customtkinter.CTkScrollableFrame(self.column2, fg_color="transparent")
            self.presets_frame.pack(fill="both", expand=True, padx=5, pady=(2, 5))
            self.update_preset_list()

            footer2 = customtkinter.CTkFrame(self.column2, fg_color="transparent", height=20)
            footer2.pack(side="bottom", fill="x", padx=5, pady=2)
            
            self.column2_width_label = customtkinter.CTkEntry(footer2, width=85, height=22, font=customtkinter.CTkFont(size=11), text_color="gray", fg_color="transparent", border_width=1)
            self.column2_width_label.pack(side="right")
            self.column2_width_label.insert(0, f"{self.column2_width} pixels")
            self.column2_width_label.bind("<Return>", lambda event: self.apply_manual_pane_size(2))

        def setup_column3(self):
            header3 = customtkinter.CTkFrame(self.column3, fg_color="transparent")
            header3.pack(fill="x", padx=5, pady=(5, 2))
            customtkinter.CTkLabel(header3, text="Automatic Profiles", font=customtkinter.CTkFont(size=15, weight="bold")).pack(side="left")
            customtkinter.CTkButton(header3, text="↺", width=28, height=28, fg_color="#34495E", hover_color="#2C3E50", command=lambda: self.reset_pane_size(3)).pack(side="right", padx=(5,0))
            customtkinter.CTkButton(header3, text="Add Rule", width=80, height=28, command=self.add_empty_autoset).pack(side="right", padx=(5,0))
            customtkinter.CTkButton(header3, text="Add Target", width=100, height=28, fg_color="#27AE60", hover_color="#2ECC71", command=lambda: self.delayed_action(self.add_current_autoset)).pack(side="right")

            self.autosets_frame = customtkinter.CTkScrollableFrame(self.column3, fg_color="transparent")
            self.autosets_frame.pack(fill="both", expand=True, padx=2, pady=2)
            self.render_autosets()
            
            footer3 = customtkinter.CTkFrame(self.column3, fg_color="transparent", height=20)
            footer3.pack(side="bottom", fill="x", padx=5, pady=2)
            
            self.column3_width_label = customtkinter.CTkEntry(footer3, width=85, height=22, font=customtkinter.CTkFont(size=11), text_color="gray", fg_color="transparent", border_width=1)
            self.column3_width_label.pack(side="right")
            self.column3_width_label.insert(0, f"{self.column3_width} pixels")
            self.column3_width_label.bind("<Return>", lambda event: self.apply_manual_pane_size(3))

        def setup_advanced_textbox(self, textbox, current_index, key, initial_text):
            try:
                textbox.configure(undo=True)
            except Exception:
                pass
            textbox._textbox.configure(undo=True, autoseparators=True, maxundo=-1)
            
            cleaned_initial = "\n".join([line.strip() for line in initial_text.split("\n")]).strip()
            textbox.insert("1.0", cleaned_initial)
            
            def sanitize_and_save(event):
                raw_text = textbox.get("1.0", "end-1c")
                cleaned_text = "\n".join([line.strip() for line in raw_text.split("\n")]).strip()
                
                if raw_text != cleaned_text:
                    textbox.delete("1.0", "end")
                    textbox.insert("1.0", cleaned_text)
                    
                self.update_autoset_data(current_index, key, cleaned_text)

            textbox.bind("<FocusOut>", sanitize_and_save)
            
            def _redo_action(event):
                try: 
                    textbox._textbox.edit_redo()
                except Exception: 
                    pass
                return "break"
                
            def _select_all_action(event):
                textbox._textbox.tag_add("sel", "1.0", "end-1c")
                textbox._textbox.mark_set("insert", "end-1c")
                textbox._textbox.see("insert")
                return "break"

            textbox._textbox.bind("<Control-y>", _redo_action)
            textbox._textbox.bind("<Control-a>", _select_all_action)

        def add_empty_autoset(self):
            new_set = {
                "executable": "", 
                "width": self.width, 
                "height": self.height, 
                "x_position": 0, 
                "y_position": 0, 
                "automatic_position": False, 
                "automatic_size": False, 
                "trigger": "On Focus", 
                "filter_mode": "Match", 
                "whitelist_filters": "", 
                "blacklist_filters": ""
            }
            self.autosets.append(new_set)
            self.save_config()
            self.render_autosets()

        def add_current_autoset(self):
            active_window = pygetwindow.getActiveWindow()
            if active_window and active_window.title != self.title():
                try:
                    window_handle = active_window._hWnd
                    _, process_id = win32process.GetWindowThreadProcessId(window_handle)
                    executable_name = self.get_process_name_cached(process_id)
                    
                    left_offset, top_offset, right_offset, bottom_offset = self.get_window_offsets(window_handle)
                    horizontal_position = active_window.left + left_offset
                    vertical_position = active_window.top + top_offset
                    window_width = active_window.width - left_offset - right_offset
                    window_height = active_window.height - top_offset - bottom_offset
                    
                    new_set = {
                        "executable": executable_name, 
                        "width": window_width, 
                        "height": window_height, 
                        "x_position": horizontal_position, 
                        "y_position": vertical_position, 
                        "automatic_position": True, 
                        "automatic_size": True, 
                        "trigger": "On Focus", 
                        "filter_mode": "Match", 
                        "whitelist_filters": "", 
                        "blacklist_filters": ""
                    }
                    self.autosets.append(new_set)
                    self.save_config()
                    self.render_autosets()
                    self.set_status(f"Added Automatic Set: {executable_name}", "#2ECC71")
                except Exception: 
                    log_exception("add_current_autoset")
                    self.set_status("Failed to add target", "#E74C3C")
            else: 
                self.set_status("No valid target found", "#E74C3C")

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
            for widget in self.autosets_frame.winfo_children(): 
                widget.destroy()
            
            for index, autoset in enumerate(self.autosets):
                card = customtkinter.CTkFrame(self.autosets_frame, corner_radius=6, border_width=1, border_color="#34495E")
                card.pack(fill="x", pady=3, padx=2)
                
                row1 = customtkinter.CTkFrame(card, fg_color="transparent")
                row1.pack(fill="x", padx=5, pady=(5, 2))
                executable_entry = customtkinter.CTkEntry(row1, placeholder_text="Target Executable", height=26)
                executable_entry.pack(side="left", fill="x", expand=True)
                executable_entry.insert(0, autoset.get("executable", ""))
                executable_entry.bind("<FocusOut>", lambda event, current_index=index, widget=executable_entry: self.update_autoset_data(current_index, "executable", widget.get()))
                
                customtkinter.CTkButton(row1, text="↑", width=26, height=26, command=lambda current_index=index: self.move_autoset(current_index, "up")).pack(side="left", padx=(4,0))
                customtkinter.CTkButton(row1, text="↓", width=26, height=26, command=lambda current_index=index: self.move_autoset(current_index, "down")).pack(side="left", padx=(2,0))
                customtkinter.CTkButton(row1, text="X", width=26, height=26, fg_color="#E74C3C", hover_color="#C0392B", command=lambda current_index=index: self.remove_autoset(current_index)).pack(side="left", padx=(4,0))

                row2 = customtkinter.CTkFrame(card, fg_color="transparent")
                row2.pack(fill="x", padx=5, pady=2)
                
                size_checkbox = customtkinter.CTkCheckBox(row2, text="Automatic Size", width=95)
                size_checkbox.configure(command=lambda current_index=index, checkbox=size_checkbox: self.update_autoset_data(current_index, "automatic_size", checkbox.get()))
                size_checkbox.pack(side="left")
                if autoset.get("automatic_size", False): 
                    size_checkbox.select()
                
                width_entry = customtkinter.CTkEntry(row2, placeholder_text="Width", width=65, height=26)
                width_entry.pack(side="left", padx=2)
                width_entry.insert(0, str(autoset.get("width", 0)))
                width_entry.bind("<FocusOut>", lambda event, current_index=index, widget=width_entry: self.update_autoset_data(current_index, "width", int(widget.get() or 0)))
                
                height_entry = customtkinter.CTkEntry(row2, placeholder_text="Height", width=65, height=26)
                height_entry.pack(side="left", padx=2)
                height_entry.insert(0, str(autoset.get("height", 0)))
                height_entry.bind("<FocusOut>", lambda event, current_index=index, widget=height_entry: self.update_autoset_data(current_index, "height", int(widget.get() or 0)))

                trigger_combobox = customtkinter.CTkComboBox(row2, values=["On Focus", "Always"], height=26, command=lambda value, current_index=index: self.update_autoset_data(current_index, "trigger", value))
                trigger_combobox.pack(side="right")
                trigger_combobox.set(autoset.get("trigger", "On Focus"))

                row3 = customtkinter.CTkFrame(card, fg_color="transparent")
                row3.pack(fill="x", padx=5, pady=2)
                
                position_checkbox = customtkinter.CTkCheckBox(row3, text="Automatic Position", width=95)
                position_checkbox.configure(command=lambda current_index=index, checkbox=position_checkbox: self.update_autoset_data(current_index, "automatic_position", checkbox.get()))
                position_checkbox.pack(side="left")
                if autoset.get("automatic_position", False): 
                    position_checkbox.select()
                
                horizontal_position_entry = customtkinter.CTkEntry(row3, placeholder_text="Horizontal", width=85, height=26)
                horizontal_position_entry.pack(side="left", padx=2)
                horizontal_position_entry.insert(0, str(autoset.get("x_position", 0)))
                horizontal_position_entry.bind("<FocusOut>", lambda event, current_index=index, widget=horizontal_position_entry: self.update_autoset_data(current_index, "x_position", int(widget.get() or 0)))
                
                vertical_position_entry = customtkinter.CTkEntry(row3, placeholder_text="Vertical", width=85, height=26)
                vertical_position_entry.pack(side="left", padx=2)
                vertical_position_entry.insert(0, str(autoset.get("y_position", 0)))
                vertical_position_entry.bind("<FocusOut>", lambda event, current_index=index, widget=vertical_position_entry: self.update_autoset_data(current_index, "y_position", int(widget.get() or 0)))

                row_filter_mode = customtkinter.CTkFrame(card, fg_color="transparent")
                row_filter_mode.pack(fill="x", padx=5, pady=2)
                customtkinter.CTkLabel(row_filter_mode, text="Filter Mode:", font=customtkinter.CTkFont(size=12)).pack(side="left", padx=(0, 5))
                filter_mode_combobox = customtkinter.CTkComboBox(row_filter_mode, values=["Match", "Include"], width=120, height=26, command=lambda value, current_index=index: self.update_autoset_data(current_index, "filter_mode", value))
                filter_mode_combobox.pack(side="left")
                filter_mode_combobox.set(autoset.get("filter_mode", "Match"))

                tabview = customtkinter.CTkTabview(card, height=110)
                tabview.pack(fill="x", padx=5, pady=(2, 5))
                tab_whitelist = tabview.add("Whitelist")
                tab_blacklist = tabview.add("Blacklist")

                whitelist_textbox = customtkinter.CTkTextbox(tab_whitelist, height=55, wrap="none", border_width=1, border_color="#34495E")
                whitelist_textbox.pack(fill="both", expand=True)
                self.setup_advanced_textbox(whitelist_textbox, index, "whitelist_filters", autoset.get("whitelist_filters", ""))

                blacklist_textbox = customtkinter.CTkTextbox(tab_blacklist, height=55, wrap="none", border_width=1, border_color="#34495E")
                blacklist_textbox.pack(fill="both", expand=True)
                self.setup_advanced_textbox(blacklist_textbox, index, "blacklist_filters", autoset.get("blacklist_filters", ""))

        def update_config_label(self):
            value = f"{self.width}x{self.height}" if self.width else "None"
            self.config_label.configure(text=f"[{value}]")

        def get_process_name_cached(self, process_id):
            try:
                process = psutil.Process(process_id)
                create_time = process.create_time()
                if process_id in self.process_identifier_cache:
                    cached_name, cached_time = self.process_identifier_cache[process_id]
                    if cached_time == create_time:
                        return cached_name
                
                name = process.name()
                self.process_identifier_cache[process_id] = (name, create_time)
                return name
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return ""

        def get_active_process_name(self):
            try:
                window_handle = win32gui.GetForegroundWindow()
                _, process_id = win32process.GetWindowThreadProcessId(window_handle)
                return self.get_process_name_cached(process_id)
            except Exception:
                return "Unknown"

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
                        self.after(0, lambda current_executable=executable: self.update_focus_display(current_executable))
                    except Exception: 
                        pass
                    time.sleep(0.5)
            threading.Thread(target=track, daemon=True).start()

        def get_window_offsets(self, window_handle):
            try:
                window_rectangle = wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(window_handle, ctypes.byref(window_rectangle))
                
                dwm_rectangle = wintypes.RECT()
                ctypes.windll.dwmapi.DwmGetWindowAttribute(window_handle, 9, ctypes.byref(dwm_rectangle), ctypes.sizeof(dwm_rectangle))
                
                left_offset = dwm_rectangle.left - window_rectangle.left
                top_offset = dwm_rectangle.top - window_rectangle.top
                right_offset = window_rectangle.right - window_rectangle.right
                bottom_offset = window_rectangle.bottom - window_rectangle.bottom
                
                return left_offset, top_offset, right_offset, bottom_offset
            except Exception:
                return 0, 0, 0, 0

        def start_automatic_enforcer(self):
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
                        window_handles = []
                        
                        if has_always_trigger:
                            def enumerate_callback(window_handle, result):
                                if win32gui.IsWindowVisible(window_handle) and win32gui.GetWindowText(window_handle):
                                    result.append(window_handle)
                            win32gui.EnumWindows(enumerate_callback, window_handles)
                        else:
                            if current_active and current_active != 0:
                                window_handles = [current_active]
                        
                        for window_handle in window_handles:
                            try:
                                _, process_id = win32process.GetWindowThreadProcessId(window_handle)
                                executable_name = self.get_process_name_cached(process_id)
                                if not executable_name: 
                                    continue
                            except Exception:
                                continue

                            window_title = win32gui.GetWindowText(window_handle)
                            is_minimized = win32gui.IsIconic(window_handle)
                            is_focused = (window_handle == current_active)
                            was_focused = (window_handle == last_focus)

                            for rule in self.autosets:
                                rule_executable = rule.get("executable", "").strip()
                                if not rule_executable or executable_name.lower() != rule_executable.lower():
                                    continue

                                filter_mode = rule.get("filter_mode", "Match")
                                raw_whitelist = rule.get("whitelist_filters", "")
                                whitelist_filters = [line.strip() for line in raw_whitelist.split("\n") if line.strip()]
                                
                                raw_blacklist = rule.get("blacklist_filters", "")
                                blacklist_filters = [line.strip() for line in raw_blacklist.split("\n") if line.strip()]

                                if blacklist_filters:
                                    blacklisted = False
                                    for filter_text in blacklist_filters:
                                        if filter_mode == "Match":
                                            if window_title.lower() == filter_text.lower():
                                                blacklisted = True
                                                break
                                        else:
                                            if filter_text.lower() in window_title.lower():
                                                blacklisted = True
                                                break
                                    if blacklisted:
                                        continue

                                if whitelist_filters:
                                    whitelisted = False
                                    for filter_text in whitelist_filters:
                                        if filter_mode == "Match":
                                            if window_title.lower() == filter_text.lower():
                                                whitelisted = True
                                                break
                                        else:
                                            if filter_text.lower() in window_title.lower():
                                                whitelisted = True
                                                break
                                    if not whitelisted:
                                        continue
                                    
                                trigger_mode = rule.get("trigger", "On Focus")
                                do_enforce = False
                                
                                if trigger_mode == "Always" and not is_minimized:
                                    do_enforce = True
                                elif trigger_mode == "On Focus" and is_focused and not was_focused:
                                    do_enforce = True
                                    
                                if do_enforce:
                                    try:
                                        window_rectangle = wintypes.RECT()
                                        ctypes.windll.user32.GetWindowRect(window_handle, ctypes.byref(window_rectangle))
                                        
                                        left_offset, top_offset, right_offset, bottom_offset = self.get_window_offsets(window_handle)
                                        
                                        needs_move = False
                                        needs_resize = False
                                        
                                        current_horizontal = window_rectangle.left + left_offset
                                        current_vertical = window_rectangle.top + top_offset
                                        current_width = (window_rectangle.right - window_rectangle.left) - left_offset - right_offset
                                        current_height = (window_rectangle.bottom - window_rectangle.top) - top_offset - bottom_offset
                                        
                                        if rule.get("automatic_position", False):
                                            if current_horizontal != rule.get("x_position", 0) or current_vertical != rule.get("y_position", 0):
                                                needs_move = True
                                                
                                        if rule.get("automatic_size", False):
                                            if current_width != rule.get("width", 0) or current_height != rule.get("height", 0):
                                                needs_resize = True

                                        if needs_resize:
                                            new_width = rule.get("width", current_width)
                                            new_height = rule.get("height", current_height)
                                            final_width = new_width + left_offset + right_offset
                                            final_height = new_height + top_offset + bottom_offset
                                            win32gui.SetWindowPos(window_handle, 0, 0, 0, final_width, final_height, 0x0002 | 0x0004 | 0x0010)
                                            if needs_move:
                                                time.sleep(0.01)

                                        if needs_move:
                                            new_horizontal = rule.get("x_position", current_horizontal)
                                            new_vertical = rule.get("y_position", current_vertical)
                                            final_horizontal = new_horizontal - left_offset
                                            final_vertical = new_vertical - top_offset
                                            win32gui.SetWindowPos(window_handle, 0, final_horizontal, final_vertical, 0, 0, 0x0001 | 0x0004 | 0x0010)
                                    except Exception:
                                        log_exception("enforcer")
                        last_focus = current_active
                    except Exception:
                        pass
            threading.Thread(target=enforcer_loop, daemon=True).start()

        def delayed_action(self, function):
            def wrapper():
                for index in range(self.countdown_value, 0, -1):
                    self.set_status(f"Action in {index} seconds...", "#F39C12", auto_reset=False)
                    time.sleep(1)
                self.after(0, function)
            threading.Thread(target=wrapper, daemon=True).start()

        def check_save(self):
            window_handle = win32gui.GetForegroundWindow()
            if window_handle:
                window_rectangle = wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(window_handle, ctypes.byref(window_rectangle))
                left_offset, top_offset, right_offset, bottom_offset = self.get_window_offsets(window_handle)
                window_width = (window_rectangle.right - window_rectangle.left) - left_offset - right_offset
                window_height = (window_rectangle.bottom - window_rectangle.top) - top_offset - bottom_offset
                self.width_entry.delete(0, "end")
                self.width_entry.insert(0, str(window_width))
                self.height_entry.delete(0, "end")
                self.height_entry.insert(0, str(window_height))
                self.update_resolution_from_user_interface()
                self.set_status("Captured active window size", "#2ECC71")

        def resize_only(self):
            window_handle = win32gui.GetForegroundWindow()
            if window_handle and self.width and self.height:
                left_offset, top_offset, right_offset, bottom_offset = self.get_window_offsets(window_handle)
                final_width = self.width + left_offset + right_offset
                final_height = self.height + top_offset + bottom_offset
                win32gui.SetWindowPos(window_handle, 0, 0, 0, final_width, final_height, 0x0002 | 0x0004 | 0x0010)
                self.set_status("Resized active window", "#2ECC71")

        def reload_user_interface_config(self):
            self.width, self.height, self.always_on_top_value, self.countdown_value, self.column1_width, self.column2_width, self.column3_width = self.load_config()
            self.width_entry.delete(0, "end")
            self.width_entry.insert(0, str(self.width))
            self.height_entry.delete(0, "end")
            self.height_entry.insert(0, str(self.height))
            self.countdown_entry.delete(0, "end")
            self.countdown_entry.insert(0, str(self.countdown_value))
            
            self.paned_window.paneconfig(self.column1, width=self.column1_width)
            self.paned_window.paneconfig(self.column2, width=self.column2_width)
            self.paned_window.paneconfig(self.column3, width=self.column3_width)
            self.update_pane_labels()
            
            if self.always_on_top_value:
                self.topmost_checkbox.select()
            else:
                self.topmost_checkbox.deselect()
                
            self.update_config_label()
            self.update_preset_list()
            self.render_autosets()
            self.set_status("Configuration Reloaded", "#3498DB")

        def move_window(self, position):
            window_handle = win32gui.GetForegroundWindow()
            if not window_handle: 
                return
            
            monitor_information = win32api.GetMonitorInfo(win32api.MonitorFromWindow(window_handle))
            work_area = monitor_information['Work']
            monitor_width, monitor_height = work_area[2] - work_area[0], work_area[3] - work_area[1]
            monitor_horizontal, monitor_vertical = work_area[0], work_area[1]
            
            window_rectangle = wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(window_handle, ctypes.byref(window_rectangle))
            
            left_offset, top_offset, right_offset, bottom_offset = self.get_window_offsets(window_handle)
            current_width = (window_rectangle.right - window_rectangle.left) - left_offset - right_offset
            current_height = (window_rectangle.bottom - window_rectangle.top) - top_offset - bottom_offset
            
            new_horizontal, new_vertical = monitor_horizontal, monitor_vertical
            
            if position in ("1", "4", "7"): 
                new_horizontal = monitor_horizontal
            elif position in ("2", "5", "8"): 
                new_horizontal = monitor_horizontal + (monitor_width - current_width) // 2
            elif position in ("3", "6", "9"): 
                new_horizontal = monitor_horizontal + monitor_width - current_width
            
            if position in ("1", "2", "3"): 
                new_vertical = monitor_vertical
            elif position in ("4", "5", "6"): 
                new_vertical = monitor_vertical + (monitor_height - current_height) // 2
            elif position in ("7", "8", "9"): 
                new_vertical = monitor_vertical + monitor_height - current_height
            
            final_horizontal = new_horizontal - left_offset
            final_vertical = new_vertical - top_offset
            final_width = current_width + left_offset + right_offset
            final_height = current_height + top_offset + bottom_offset
            
            win32gui.SetWindowPos(window_handle, 0, final_horizontal, final_vertical, final_width, final_height, 0x0004 | 0x0010)
            self.set_status(f"Moved Window to position {position}", "#2ECC71")

        def setup_tray_icon(self):
            if self.tray_icon:
                try:
                    self.tray_icon.stop()
                except Exception:
                    pass
                self.tray_icon = None

            image = self.create_app_icon()
            menu = pystray.Menu(
                pystray.MenuItem("Show Window", self.show_from_tray, default=True),
                pystray.MenuItem("Exit", self.exit_from_tray)
            )
            self.tray_icon = pystray.Icon("Window Workspace", image, "Window Workspace", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()

        def hide_to_tray(self):
            self.withdraw()
            self.setup_tray_icon()

        def show_from_tray(self, icon=None, item=None):
            if self.tray_icon:
                try:
                    self.tray_icon.stop()
                except Exception:
                    pass
                self.tray_icon = None
            self.after(0, self.deiconify)
            self.after(100, self.lift)

        def exit_from_tray(self, icon=None, item=None):
            if self.tray_icon:
                try:
                    self.tray_icon.stop()
                except Exception:
                    pass
                self.tray_icon = None
            self.after(0, self.destroy)
            sys.exit(0)

    if __name__ == "__main__":
        console_window = win32console.GetConsoleWindow()
        if console_window:
            win32gui.ShowWindow(console_window, 0)

        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme("blue")

        application = WindowManagerGUI()
        application.mainloop()

except Exception as exception_instance:
    error_message = traceback.format_exc()
    try:
        import ctypes
        console = ctypes.windll.kernel32.GetConsoleWindow()
        if console:
            ctypes.windll.user32.ShowWindow(console, 5)
    except Exception:
        pass
    try:
        import pyperclip
        pyperclip.copy(error_message)
        print("Error details copied to clipboard.")
    except Exception:
        pass
    print("Critical Error Encountered:\n" + error_message)
    input("Press Enter to close this window...")
