import customtkinter as ctk
import os
import sys
import time
import ctypes
import subprocess
import cv2
import threading
import configparser
from tkinter import filedialog
from pynput import keyboard
from windows_capture import WindowsCapture, Frame, InternalCaptureControl

try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_int(-4))
except AttributeError:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except:
        pass

FFMPEG_PATH = r"D:\.data\Apps\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{os.path.abspath(__file__)}"', None, 1)
    sys.exit()

console_window = ctypes.windll.kernel32.GetConsoleWindow()
if console_window:
    ctypes.windll.user32.ShowWindow(console_window, 0)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class CaptureApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Screen Capturer")
        self.resizable(False, False)
        
        app_width = 400
        app_height = 560
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_position = int((screen_width / 2) - (app_width / 2))
        y_position = int((screen_height / 2) - (app_height / 2))
        self.geometry(f"{app_width}x{app_height}+{x_position}+{y_position}")
        
        self.is_capturing = False
        self.engine_running = False
        self.stop_capture_flag = threading.Event()
        self.pressed_keys = set()
        self.main_listener = None
        
        self.config = configparser.ConfigParser()
        self.config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
        self.load_config()
        
        self.setup_ui()
        self.apply_initial_states()

    def load_config(self):
        if os.path.exists(self.config_path):
            self.config.read(self.config_path)
        if not self.config.has_section("Settings"):
            self.config.add_section("Settings")
            
        self.fps_val = self.config.get("Settings", "fps", fallback="60")
        self.min_time_val = self.config.get("Settings", "min_time", fallback="0")
        self.max_time_val = self.config.get("Settings", "max_time", fallback="5")
        self.format_val = self.config.get("Settings", "format", fallback="png")
        self.export_val = self.config.getboolean("Settings", "export_video", fallback=True)
        self.topmost_val = self.config.getboolean("Settings", "always_on_top", fallback=False)
        self.hide_val = self.config.getboolean("Settings", "hide_capture", fallback=True)
        self.output_dir = self.config.get("Settings", "output_path", fallback="R:/Captured")
        self.hotkey_str = self.config.get("Settings", "hotkey", fallback="F9")
        self.current_hotkey = self.string_to_keys(self.hotkey_str)

    def save_config(self, *args):
        self.config["Settings"]["fps"] = self.fps_entry.get()
        self.config["Settings"]["min_time"] = self.min_time_entry.get()
        self.config["Settings"]["max_time"] = self.max_time_entry.get()
        self.config["Settings"]["format"] = self.format_combobox.get()
        self.config["Settings"]["export_video"] = str(self.export_checkbox.get())
        self.config["Settings"]["always_on_top"] = str(self.always_on_top_checkbox.get())
        self.config["Settings"]["hide_capture"] = str(self.hide_capture_checkbox.get())
        self.config["Settings"]["output_path"] = self.output_entry.get()
        self.config["Settings"]["hotkey"] = self.btn_bind.cget("text")
        
        with open(self.config_path, "w") as configfile:
            self.config.write(configfile)

    def string_to_keys(self, hotkey_str):
        keys = set()
        parts = [p.strip().lower() for p in hotkey_str.split('+')]
        for p in parts:
            if hasattr(keyboard.Key, p):
                keys.add(getattr(keyboard.Key, p))
            else:
                try:
                    keys.add(keyboard.KeyCode.from_char(p))
                except Exception:
                    pass
        if not keys:
            keys = {keyboard.Key.f9}
        return keys

    def setup_ui(self):
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=15, pady=15)

        header_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(header_frame, text="Capture Settings", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w")

        settings_frame = ctk.CTkFrame(main_container, corner_radius=8, fg_color="#2B2B2B")
        settings_frame.pack(fill="x", pady=(0, 15))
        
        row1 = ctk.CTkFrame(settings_frame, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(row1, text="Target FPS", font=ctk.CTkFont(size=13)).pack(side="left")
        self.fps_entry = ctk.CTkEntry(row1, width=80, height=28)
        self.fps_entry.insert(0, self.fps_val)
        self.fps_entry.pack(side="right")
        self.fps_entry.bind("<KeyRelease>", self.save_config)

        row2 = ctk.CTkFrame(settings_frame, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(row2, text="Minimum Duration (s)", font=ctk.CTkFont(size=13)).pack(side="left")
        self.min_time_entry = ctk.CTkEntry(row2, width=80, height=28)
        self.min_time_entry.insert(0, self.min_time_val)
        self.min_time_entry.pack(side="right")
        self.min_time_entry.bind("<KeyRelease>", self.save_config)

        row3 = ctk.CTkFrame(settings_frame, fg_color="transparent")
        row3.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(row3, text="Maximum Duration (s)", font=ctk.CTkFont(size=13)).pack(side="left")
        self.max_time_entry = ctk.CTkEntry(row3, width=80, height=28)
        self.max_time_entry.insert(0, self.max_time_val)
        self.max_time_entry.pack(side="right")
        self.max_time_entry.bind("<KeyRelease>", self.save_config)

        row4 = ctk.CTkFrame(settings_frame, fg_color="transparent")
        row4.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(row4, text="Format", font=ctk.CTkFont(size=13)).pack(side="left")
        self.format_combobox = ctk.CTkComboBox(row4, values=["png", "jpg", "bmp"], width=80, height=28, command=self.save_config)
        self.format_combobox.set(self.format_val)
        self.format_combobox.pack(side="right")

        path_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        path_frame.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(path_frame, text="Output Path", font=ctk.CTkFont(size=13)).pack(side="left")
        self.btn_browse = ctk.CTkButton(path_frame, text="Browse", width=60, height=28, fg_color="#34495E", hover_color="#2C3E50", command=self.browse_path)
        self.btn_browse.pack(side="right", padx=(5, 0))
        self.output_entry = ctk.CTkEntry(path_frame, height=28)
        self.output_entry.insert(0, self.output_dir)
        self.output_entry.pack(side="right", fill="x", expand=True)
        self.output_entry.bind("<KeyRelease>", self.save_config)

        options_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        options_frame.pack(fill="x", pady=(0, 15))
        
        self.export_checkbox = ctk.CTkCheckBox(options_frame, text="Compile Video Output", font=ctk.CTkFont(size=13), command=self.save_config)
        if self.export_val: self.export_checkbox.select()
        self.export_checkbox.grid(row=0, column=0, sticky="w", pady=5, padx=(0, 10))

        self.always_on_top_checkbox = ctk.CTkCheckBox(options_frame, text="Always On Top", command=lambda: [self.toggle_topmost(), self.save_config()], font=ctk.CTkFont(size=13))
        if self.topmost_val: self.always_on_top_checkbox.select()
        self.always_on_top_checkbox.grid(row=0, column=1, sticky="w", pady=5, padx=10)

        self.hide_capture_checkbox = ctk.CTkCheckBox(options_frame, text="Hide From Capture", command=lambda: [self.toggle_hide_capture(), self.save_config()], font=ctk.CTkFont(size=13))
        if self.hide_val: self.hide_capture_checkbox.select()
        self.hide_capture_checkbox.grid(row=1, column=0, columnspan=2, sticky="w", pady=5, padx=(0, 10))

        hotkey_frame = ctk.CTkFrame(main_container, fg_color="transparent")
        hotkey_frame.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(hotkey_frame, text="Hotkey", font=ctk.CTkFont(size=13)).pack(side="left")
        self.btn_bind = ctk.CTkButton(hotkey_frame, text=self.hotkey_str.upper(), width=120, height=28, fg_color="#34495E", hover_color="#2C3E50", command=self.bind_hotkey)
        self.btn_bind.pack(side="right")

        self.btn_engine = ctk.CTkButton(main_container, text="Start Engine", height=36, font=ctk.CTkFont(size=14, weight="bold"), fg_color="#1F6AA5", command=self.toggle_engine)
        self.btn_engine.pack(fill="x", pady=(5, 10))
        
        self.btn_open_folder = ctk.CTkButton(main_container, text="Open Output Folder", height=36, font=ctk.CTkFont(size=14, weight="bold"), fg_color="#34495E", hover_color="#2C3E50", command=self.open_output_folder)
        self.btn_open_folder.pack(fill="x", pady=(0, 15))

        footer_frame = ctk.CTkFrame(main_container, fg_color="transparent", height=20)
        footer_frame.pack(side="bottom", fill="x")
        self.status_label = ctk.CTkLabel(footer_frame, text="Ready", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray")
        self.status_label.pack(side="left")

    def apply_initial_states(self):
        self.toggle_topmost()
        self.toggle_hide_capture()
        os.makedirs(self.output_entry.get(), exist_ok=True)

    def update_status(self, text, color="gray"):
        self.after(0, lambda: self.status_label.configure(text=text, text_color=color))

    def browse_path(self):
        folder = filedialog.askdirectory(initialdir=self.output_entry.get())
        if folder:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, folder)
            self.save_config()

    def toggle_topmost(self):
        self.attributes('-topmost', self.always_on_top_checkbox.get())

    def toggle_hide_capture(self):
        hwnd = int(self.wm_frame(), 16)
        if self.hide_capture_checkbox.get():
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x00000011)
        else:
            ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0)

    def open_output_folder(self):
        try:
            target_path = os.path.abspath(self.output_entry.get())
            os.makedirs(target_path, exist_ok=True)
            os.startfile(target_path)
        except Exception:
            self.update_status("Failed to Open Folder", "#E74C3C")

    def get_hotkey_string(self, keys):
        names = []
        for k in keys:
            name = getattr(k, 'char', None) or getattr(k, 'name', str(k))
            if name.startswith('ctrl'): name = 'ctrl'
            elif name.startswith('shift'): name = 'shift'
            elif name.startswith('alt'): name = 'alt'
            names.append(name.upper())
        final_names = list(set(names))
        final_names.sort(key=lambda x: (x not in ['CTRL', 'SHIFT', 'ALT'], x))
        return " + ".join(final_names)

    def bind_hotkey(self):
        self.btn_bind.configure(text="Listening...")
        self.update_status("Awaiting hotkey input", "#3498DB")
        
        temp_combo = set()
        
        def on_press(key):
            temp_combo.add(key)
            
        def on_release(key):
            self.current_hotkey = set(temp_combo)
            combo_str = self.get_hotkey_string(self.current_hotkey)
            self.after(0, lambda: [self.btn_bind.configure(text=combo_str), self.save_config()])
            self.update_status("Hotkey updated", "#2ECC71")
            return False
            
        threading.Thread(target=lambda: keyboard.Listener(on_press=on_press, on_release=on_release).start(), daemon=True).start()

    def toggle_engine(self):
        if not self.engine_running:
            self.engine_running = True
            self.btn_engine.configure(text="Stop Engine", fg_color="#E74C3C", hover_color="#C0392B")
            combo_str = self.get_hotkey_string(self.current_hotkey)
            self.update_status(f"Engine Active - Hold {combo_str} to Capture", "#2ECC71")
            
            self.pressed_keys.clear()
            self.main_listener = keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release)
            self.main_listener.start()
        else:
            self.engine_running = False
            self.btn_engine.configure(text="Start Engine", fg_color="#1F6AA5", hover_color="#144870")
            self.update_status("Engine Inactive", "gray")
            if self.main_listener:
                self.main_listener.stop()

    def on_key_press(self, key):
        self.pressed_keys.add(key)
        if self.current_hotkey.issubset(self.pressed_keys) and not self.is_capturing:
            self.is_capturing = True
            self.stop_capture_flag.clear()
            threading.Thread(target=self.run_capture_session, daemon=True).start()

    def on_key_release(self, key):
        if self.is_capturing and key in self.current_hotkey:
            self.stop_capture_flag.set()
        if key in self.pressed_keys:
            self.pressed_keys.remove(key)

    def get_next_session_folder(self):
        out_dir = self.output_entry.get()
        os.makedirs(out_dir, exist_ok=True)
        existing = [d for d in os.listdir(out_dir) if os.path.isdir(os.path.join(out_dir, d)) and d.isdigit()]
        next_num = max([int(d) for d in existing]) + 1 if existing else 1
        path = os.path.join(out_dir, str(next_num))
        os.makedirs(path, exist_ok=True)
        return path

    def run_capture_session(self):
        session_dir = self.get_next_session_folder()
        
        try:
            min_time = float(self.min_time_entry.get())
        except ValueError:
            min_time = 0.0
            
        try:
            max_time = float(self.max_time_entry.get())
        except ValueError:
            max_time = 5.0
            
        max_time = max(max_time, min_time)
        
        self.update_status("Capturing", "#F39C12")
        capture = WindowsCapture(cursor_capture=False)
        
        state = {"start": None, "buffer": []}

        @capture.event
        def on_frame_arrived(frame: Frame, capture_control: InternalCaptureControl):
            current = time.perf_counter()
            if state["start"] is None:
                state["start"] = current

            elapsed = current - state["start"]
            
            if elapsed >= max_time:
                capture_control.stop()
            elif self.stop_capture_flag.is_set() and elapsed >= min_time:
                capture_control.stop()
            else:
                state["buffer"].append(frame.frame_buffer.copy())

        @capture.event
        def on_closed():
            pass

        capture.start()
        
        total = len(state["buffer"])
        if total > 0:
            self.update_status(f"Saving {total} Frames", "#3498DB")
            img_format = self.format_combobox.get()
            
            if img_format == "png":
                flags = [int(cv2.IMWRITE_PNG_COMPRESSION), 0]
            elif img_format == "jpg":
                flags = [int(cv2.IMWRITE_JPEG_QUALITY), 100]
            else:
                flags = []

            for i, raw_frame in enumerate(state["buffer"]):
                path = os.path.join(session_dir, f"image_{i+1:03d}.{img_format}")
                cv2.imwrite(path, raw_frame, flags)

            if self.export_checkbox.get():
                duration = time.perf_counter() - state["start"]
                actual_fps = total / duration if duration > 0 else total
                self.compile_video(session_dir, actual_fps, img_format)
            else:
                self.update_status("Capture Complete", "#2ECC71")
        else:
            self.update_status("Error: No Frames Captured", "#E74C3C")
            
        self.is_capturing = False

    def compile_video(self, session_dir, input_fps, img_format):
        self.update_status("Encoding Video", "#3498DB")
        video_out = os.path.join(session_dir, "output.mp4")
        pattern = os.path.join(session_dir, f"image_%03d.{img_format}")
        
        try:
            target_fps = str(int(self.fps_entry.get()))
        except ValueError:
            target_fps = "60"
        
        cmd = [
            FFMPEG_PATH, "-y",
            "-framerate", str(input_fps),
            "-i", pattern,
            "-c:v", "libx264",
            "-r", target_fps,
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            video_out
        ]
        
        try:
            proc = subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
            proc.wait()
            
            if proc.returncode == 0:
                self.update_status(f"Completed: {os.path.basename(session_dir)}", "#2ECC71")
            else:
                self.update_status("Compilation Failed", "#E74C3C")
        except Exception:
            self.update_status("FFmpeg Missing", "#E74C3C")

if __name__ == "__main__":
    app = CaptureApp()
    app.mainloop()
