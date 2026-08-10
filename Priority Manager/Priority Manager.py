import sys
import os
import ctypes
import subprocess
import importlib.util
import traceback
import time
import threading
import configparser
import tkinter

def check_administrator_privileges():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def restart_as_administrator():
    executable_path = sys.executable
    script_path = os.path.abspath(sys.argv[0])
    working_directory_path = os.path.dirname(script_path)
    arguments_string = f'"{script_path}"'
    if len(sys.argv) > 1:
        arguments_string += " " + " ".join([f'"{argument}"' for argument in sys.argv[1:]])
    
    execution_result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        executable_path,
        arguments_string,
        working_directory_path,
        1
    )
    if execution_result <= 32:
        print("Failed to request administrator privileges.")
        input("Press Enter to manually terminate the program...")
        sys.exit(1)
    sys.exit(0)

def hide_command_prompt_window():
    console_window_handle = ctypes.windll.kernel32.GetConsoleWindow()
    if console_window_handle != 0:
        ctypes.windll.user32.ShowWindow(console_window_handle, 0)

def verify_and_update_required_libraries():
    required_modules_dictionary = {
        "customtkinter": "customtkinter",
        "psutil": "psutil",
        "win32gui": "pywin32",
        "pystray": "pystray",
        "PIL": "Pillow",
        "pyperclip": "pyperclip"
    }
    for module_name, package_name in required_modules_dictionary.items():
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", package_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

if __name__ == "__main__":
    if not check_administrator_privileges():
        restart_as_administrator()

    verify_and_update_required_libraries()

    hide_command_prompt_window()

    import psutil
    import win32gui
    import win32process
    import pystray
    import PIL.Image
    import PIL.ImageDraw
    import customtkinter
    import pyperclip

    customtkinter.set_appearance_mode("Dark")
    customtkinter.set_default_color_theme("blue")

    try:
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_int(-4))
        except AttributeError:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                pass

        class PriorityManagerApplication(customtkinter.CTk):
            def __init__(self):
                super().__init__()
                self.title("Priority Manager")
                
                application_width = 1002
                application_height = 664
                screen_width = self.winfo_screenwidth()
                screen_height = self.winfo_screenheight()
                horizontal_position = int((screen_width / 2) - (application_width / 2))
                vertical_position = int((screen_height / 2) - (application_height / 2))
                self.geometry(f"{application_width}x{application_height}+{horizontal_position}+{vertical_position}")
                self.resizable(True, True)
                self.minsize(1002, 664)
                
                self.configuration_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
                self.configuration_parser = configparser.ConfigParser()
                self.configuration_parser.optionxform = str
                
                self.priority_mapping_dictionary = {
                    "Idle": psutil.IDLE_PRIORITY_CLASS,
                    "Below Normal": psutil.BELOW_NORMAL_PRIORITY_CLASS,
                    "Normal": psutil.NORMAL_PRIORITY_CLASS,
                    "Above Normal": psutil.ABOVE_NORMAL_PRIORITY_CLASS,
                    "High": psutil.HIGH_PRIORITY_CLASS,
                    "Realtime": psutil.REALTIME_PRIORITY_CLASS
                }
                self.priority_levels_list = list(self.priority_mapping_dictionary.keys())
                
                self.tray_icon = None
                self.is_resizing = False
                self.resize_timer = None
                
                self.load_configuration_from_file()
                
                self.running_thread_flag = True
                self.build_user_interface()
                self.apply_always_on_top_setting()
                
                self.bind("<Configure>", self.on_window_configure)
                self.protocol("WM_DELETE_WINDOW", self.close_application_directly)
                
                self.background_worker_thread = threading.Thread(target=self.manage_process_priorities_loop, daemon=True)
                self.background_worker_thread.start()

                self.tray_monitor_thread = threading.Thread(target=self.monitor_system_tray_loop, daemon=True)
                self.tray_monitor_thread.start()

            def trigger_action_animation(self, target_widget):
                original_color = target_widget.cget("fg_color")
                target_widget.configure(fg_color="#3B82F6")
                self.after(150, lambda: target_widget.configure(fg_color=original_color))

            def execute_action_with_animation(self, widget_object, callback_function):
                self.trigger_action_animation(widget_object)
                callback_function()

            def on_window_configure(self, event_object):
                if event_object.widget == self:
                    self.is_resizing = True
                    if self.resize_timer:
                        self.after_cancel(self.resize_timer)
                    self.resize_timer = self.after(300, self.stop_window_resize)

            def stop_window_resize(self):
                self.is_resizing = False

            def start_paned_resize(self, event_object):
                self.is_resizing = True

            def stop_paned_resize(self, event_object):
                self.is_resizing = False
                self.save_configuration_to_file()

            def load_configuration_from_file(self):
                if not os.path.exists(self.configuration_file_path):
                    self.configuration_parser["Settings"] = {
                        "active_profile": "Default",
                        "focus_delay_milliseconds": "300",
                        "process_scan_delay_milliseconds": "2500",
                        "always_on_top": "False",
                        "column1_width": "350",
                        "column2_width": "630"
                    }
                    self.configuration_parser["Profile_Default"] = {}
                    self.save_configuration_to_file()
                else:
                    self.configuration_parser.read(self.configuration_file_path)

            def write_configuration_to_disk(self):
                try:
                    with open(self.configuration_file_path, "w") as file_pointer:
                        self.configuration_parser.write(file_pointer)
                    
                    with open(self.configuration_file_path, "r") as file_pointer:
                        configuration_file_lines = file_pointer.readlines()
                    
                    cleaned_configuration_lines = [line_content for line_content in configuration_file_lines if line_content.strip()]
                    
                    with open(self.configuration_file_path, "w") as file_pointer:
                        for line_content in cleaned_configuration_lines:
                            file_pointer.write(line_content if line_content.endswith("\n") else line_content + "\n")
                except Exception:
                    pass

            def save_configuration_to_file(self):
                if hasattr(self, "column1") and hasattr(self, "column2"):
                    try:
                        self.configuration_parser["Settings"]["column1_width"] = str(self.column1.winfo_width())
                        self.configuration_parser["Settings"]["column2_width"] = str(self.column2.winfo_width())
                    except Exception:
                        pass

                threading.Thread(target=self.write_configuration_to_disk, daemon=True).start()

            def build_user_interface(self):
                main_container_frame = customtkinter.CTkFrame(self, fg_color="#121212", border_width=1, border_color="#000000")
                main_container_frame.pack(fill="both", expand=True, padx=5, pady=5)
                
                column1_saved_width = int(self.configuration_parser["Settings"].get("column1_width", "350"))
                column2_saved_width = int(self.configuration_parser["Settings"].get("column2_width", "630"))

                self.paned_window = tkinter.PanedWindow(main_container_frame, orient="horizontal", borderwidth=0, sashwidth=6, bg="#000000", opaqueresize=True)
                self.paned_window.pack(fill="both", expand=True)
                
                self.paned_window.bind("<ButtonPress-1>", self.start_paned_resize)
                self.paned_window.bind("<ButtonRelease-1>", self.stop_paned_resize)
                
                self.column1 = customtkinter.CTkFrame(self.paned_window, width=column1_saved_width, fg_color="#1E1E1E", border_width=1, border_color="#000000")
                self.column2 = customtkinter.CTkFrame(self.paned_window, width=column2_saved_width, fg_color="#1E1E1E", border_width=1, border_color="#000000")
                
                self.paned_window.add(self.column1, minsize=320)
                self.paned_window.paneconfig(self.column1, width=column1_saved_width)
                
                self.paned_window.add(self.column2, minsize=400)
                self.paned_window.paneconfig(self.column2, width=column2_saved_width)
                
                self.setup_column1()
                self.setup_column2()

            def setup_column1(self):
                profile_header_frame = customtkinter.CTkFrame(self.column1, fg_color="transparent")
                profile_header_frame.pack(fill="x", padx=10, pady=10)
                customtkinter.CTkLabel(profile_header_frame, text="Active Profile", font=customtkinter.CTkFont(size=15, weight="bold"), text_color="#E0E0E0").pack(anchor="w")
                
                self.profile_string_variable = customtkinter.StringVar(value=self.configuration_parser["Settings"].get("active_profile", "Default"))
                self.profile_combobox = customtkinter.CTkComboBox(profile_header_frame, variable=self.profile_string_variable, command=self.change_active_profile, fg_color="#2A2A2A", button_color="#3A3A3A", dropdown_fg_color="#2A2A2A", border_width=1, border_color="#000000")
                self.profile_combobox._dropdown_menu.configure(relief="flat", borderwidth=0)
                self.profile_combobox.pack(fill="x", pady=(5, 10))
                self.update_profile_dropdown_list()
                
                profile_actions_frame = customtkinter.CTkFrame(profile_header_frame, fg_color="transparent")
                profile_actions_frame.pack(fill="x")
                self.add_profile_button = customtkinter.CTkButton(profile_actions_frame, text="Add Profile", command=lambda: self.execute_action_with_animation(self.add_profile_button, self.create_new_profile_dialog), fg_color="#1F6AA5", hover_color="#2980B9", border_width=1, border_color="#000000")
                self.add_profile_button.pack(side="left", expand=True, padx=(0, 2))
                
                self.delete_profile_button = customtkinter.CTkButton(profile_actions_frame, text="Delete Profile", command=lambda: self.execute_action_with_animation(self.delete_profile_button, self.remove_current_profile), fg_color="#C0392B", hover_color="#E74C3C", border_width=1, border_color="#000000")
                self.delete_profile_button.pack(side="right", expand=True, padx=(2, 0))
                
                status_frame = customtkinter.CTkFrame(self.column1, fg_color="transparent")
                status_frame.pack(fill="x", padx=10, pady=10)
                customtkinter.CTkLabel(status_frame, text="Current Focus Status", font=customtkinter.CTkFont(size=15, weight="bold"), text_color="#E0E0E0").pack(anchor="w")
                
                self.focus_box = customtkinter.CTkTextbox(status_frame, height=36, corner_radius=6, fg_color="#2A2A2A", text_color="#2ECC71", font=customtkinter.CTkFont(size=12, weight="bold"), border_width=1, border_color="#000000")
                self.focus_box.pack(fill="x", pady=(5, 0))
                self.focus_box.configure(state="disabled")
                
                settings_frame = customtkinter.CTkFrame(self.column1, fg_color="transparent")
                settings_frame.pack(fill="x", padx=10, pady=10)
                customtkinter.CTkLabel(settings_frame, text="Global Settings", font=customtkinter.CTkFont(size=15, weight="bold"), text_color="#E0E0E0").pack(anchor="w")
                
                delay_settings_frame = customtkinter.CTkFrame(settings_frame, fg_color="transparent")
                delay_settings_frame.pack(fill="x", pady=5)
                customtkinter.CTkLabel(delay_settings_frame, text="Focus Delay (milliseconds):", text_color="#CCCCCC").pack(side="left")
                
                self.focus_delay_string_variable = customtkinter.StringVar(value=self.configuration_parser["Settings"].get("focus_delay_milliseconds", "300"))
                self.focus_delay_string_variable.trace_add("write", lambda name_parameter, index_parameter, mode_parameter: self.on_delay_settings_change())
                self.focus_delay_entry = customtkinter.CTkEntry(delay_settings_frame, width=80, textvariable=self.focus_delay_string_variable, fg_color="#2A2A2A", border_width=1, border_color="#000000")
                self.focus_delay_entry.pack(side="right")
                
                scan_settings_frame = customtkinter.CTkFrame(settings_frame, fg_color="transparent")
                scan_settings_frame.pack(fill="x", pady=5)
                customtkinter.CTkLabel(scan_settings_frame, text="Scan Delay (milliseconds):", text_color="#CCCCCC").pack(side="left")
                
                self.scan_delay_string_variable = customtkinter.StringVar(value=self.configuration_parser["Settings"].get("process_scan_delay_milliseconds", "2500"))
                self.scan_delay_string_variable.trace_add("write", lambda name_parameter, index_parameter, mode_parameter: self.on_delay_settings_change())
                self.scan_delay_entry = customtkinter.CTkEntry(scan_settings_frame, width=80, textvariable=self.scan_delay_string_variable, fg_color="#2A2A2A", border_width=1, border_color="#000000")
                self.scan_delay_entry.pack(side="right")
                
                self.always_on_top_boolean_variable = customtkinter.BooleanVar(value=self.configuration_parser["Settings"].getboolean("always_on_top", fallback=False))
                self.always_on_top_checkbox = customtkinter.CTkCheckBox(settings_frame, text="Always on Top", variable=self.always_on_top_boolean_variable, command=self.toggle_always_on_top, text_color="#CCCCCC")
                self.always_on_top_checkbox.pack(anchor="w", pady=(10, 5))
                
                footer_action_frame = customtkinter.CTkFrame(self.column1, fg_color="transparent")
                footer_action_frame.pack(side="bottom", fill="x", padx=10, pady=10)
                
                self.open_source_button = customtkinter.CTkButton(footer_action_frame, text="Open Source Folder", command=lambda: self.execute_action_with_animation(self.open_source_button, self.open_source_folder), fg_color="#1F6AA5", hover_color="#2980B9", border_width=1, border_color="#000000")
                self.open_source_button.pack(fill="x", pady=(0, 5))
                
                self.minimize_tray_button = customtkinter.CTkButton(footer_action_frame, text="Minimize to System Tray", command=lambda: self.execute_action_with_animation(self.minimize_tray_button, self.hide_to_tray), fg_color="#2C3E50", hover_color="#34495E", border_width=1, border_color="#000000")
                self.minimize_tray_button.pack(fill="x")

            def setup_column2(self):
                right_header_frame = customtkinter.CTkFrame(self.column2, fg_color="transparent")
                right_header_frame.pack(fill="x", padx=10, pady=10)
                customtkinter.CTkLabel(right_header_frame, text="Configured Programs", font=customtkinter.CTkFont(size=15, weight="bold"), text_color="#E0E0E0").pack(side="left")
                
                search_frame = customtkinter.CTkFrame(self.column2, fg_color="transparent")
                search_frame.pack(fill="x", padx=10, pady=(0, 10))
                self.search_string_variable = customtkinter.StringVar()
                self.search_string_variable.trace_add("write", lambda name_parameter, index_parameter, mode_parameter: self.render_programs_list())
                self.search_entry = customtkinter.CTkEntry(search_frame, textvariable=self.search_string_variable, placeholder_text="Search Executable Name / Title...", fg_color="#2A2A2A", border_width=1, border_color="#000000")
                self.search_entry.pack(fill="x")
                
                add_program_frame = customtkinter.CTkFrame(self.column2, corner_radius=8, fg_color="#2A2A2A", border_width=1, border_color="#000000")
                add_program_frame.pack(fill="x", padx=10, pady=(0, 10))
                
                program_inputs_frame = customtkinter.CTkFrame(add_program_frame, fg_color="transparent")
                program_inputs_frame.pack(fill="x", padx=10, pady=10)
                
                self.program_name_entry = customtkinter.CTkEntry(program_inputs_frame, placeholder_text="Executable Name", fg_color="#1E1E1E", border_width=1, border_color="#000000")
                self.program_name_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
                
                self.add_program_button = customtkinter.CTkButton(program_inputs_frame, text="Add Program", width=110, command=lambda: self.execute_action_with_animation(self.add_program_button, self.add_manual_program), fg_color="#27AE60", hover_color="#2ECC71", border_width=1, border_color="#000000")
                self.add_program_button.pack(side="right", padx=(5, 0))
                
                self.fetch_program_button = customtkinter.CTkButton(program_inputs_frame, text="Fetch Active Window", width=130, command=lambda: self.execute_action_with_animation(self.fetch_program_button, self.fetch_and_add_active_program), fg_color="#1F6AA5", hover_color="#2980B9", border_width=1, border_color="#000000")
                self.fetch_program_button.pack(side="right")
                
                priorities_frame = customtkinter.CTkFrame(add_program_frame, fg_color="transparent")
                priorities_frame.pack(fill="x", padx=10, pady=(0, 10))
                
                customtkinter.CTkLabel(priorities_frame, text="Focus Priority:", text_color="#CCCCCC").pack(side="left", padx=(0, 5))
                self.focus_priority_combobox = customtkinter.CTkComboBox(priorities_frame, values=self.priority_levels_list, width=110, fg_color="#1E1E1E", button_color="#3A3A3A", dropdown_fg_color="#2A2A2A", border_width=1, border_color="#000000")
                self.focus_priority_combobox._dropdown_menu.configure(relief="flat", borderwidth=0)
                self.focus_priority_combobox.set("High")
                self.focus_priority_combobox.pack(side="left", padx=(0, 15))
                
                customtkinter.CTkLabel(priorities_frame, text="Unfocus Priority:", text_color="#CCCCCC").pack(side="left", padx=(0, 5))
                self.unfocus_priority_combobox = customtkinter.CTkComboBox(priorities_frame, values=self.priority_levels_list, width=110, fg_color="#1E1E1E", button_color="#3A3A3A", dropdown_fg_color="#2A2A2A", border_width=1, border_color="#000000")
                self.unfocus_priority_combobox._dropdown_menu.configure(relief="flat", borderwidth=0)
                self.unfocus_priority_combobox.set("Normal")
                self.unfocus_priority_combobox.pack(side="left")

                list_header_frame = customtkinter.CTkFrame(self.column2, fg_color="#2A2A2A", border_width=1, border_color="#000000")
                list_header_frame.pack(fill="x", padx=10, pady=(0, 2))

                header_left_label = customtkinter.CTkLabel(list_header_frame, text="Program Name", font=customtkinter.CTkFont(size=12, weight="bold"), text_color="#AAAAAA")
                header_left_label.pack(side="left", padx=10, pady=4)

                header_right_frame = customtkinter.CTkFrame(list_header_frame, fg_color="transparent")
                header_right_frame.pack(side="right", padx=10, pady=4)

                header_unfocus_label = customtkinter.CTkLabel(header_right_frame, text="Unfocus", font=customtkinter.CTkFont(size=12, weight="bold"), text_color="#AAAAAA", width=100)
                header_unfocus_label.pack(side="right", padx=(2, 0))

                header_focus_label = customtkinter.CTkLabel(header_right_frame, text="Focus", font=customtkinter.CTkFont(size=12, weight="bold"), text_color="#AAAAAA", width=100)
                header_focus_label.pack(side="right", padx=(10, 2))

                header_move_label = customtkinter.CTkLabel(header_right_frame, text="Order", font=customtkinter.CTkFont(size=12, weight="bold"), text_color="#AAAAAA", width=62)
                header_move_label.pack(side="right", padx=(0, 10))
                
                self.programs_scrollable_frame = customtkinter.CTkScrollableFrame(self.column2, fg_color="transparent")
                self.programs_scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)
                
                self.render_programs_list()

            def update_current_focus_status_display(self, executable_name, is_configured):
                display_text = f"> Active Focus: {executable_name}"
                if is_configured:
                    display_text += " (Configured)"
                self.focus_box.configure(state="normal")
                self.focus_box.delete("1.0", "end")
                self.focus_box.insert("1.0", display_text)
                self.focus_box.configure(state="disabled")

            def update_profile_dropdown_list(self):
                profiles_list = [section.replace("Profile_", "") for section in self.configuration_parser.sections() if section.startswith("Profile_")]
                self.profile_combobox.configure(values=profiles_list)

            def change_active_profile(self, selected_profile_name):
                self.configuration_parser["Settings"]["active_profile"] = selected_profile_name
                self.save_configuration_to_file()
                self.render_programs_list()

            def create_new_profile_dialog(self):
                dialog_window = customtkinter.CTkToplevel(self)
                dialog_window.title("New Profile")
                dialog_window.geometry("300x150")
                dialog_window.resizable(False, False)
                dialog_window.attributes("-topmost", True)
                dialog_window.configure(fg_color="#1E1E1E")
                
                customtkinter.CTkLabel(dialog_window, text="Enter Profile Name:", text_color="#E0E0E0").pack(pady=(15, 5))
                profile_name_entry = customtkinter.CTkEntry(dialog_window, width=200, fg_color="#2A2A2A", border_width=1, border_color="#000000")
                profile_name_entry.pack(pady=5)
                
                def save_new_profile_action():
                    new_profile_name = profile_name_entry.get().strip()
                    if new_profile_name:
                        section_name = f"Profile_{new_profile_name}"
                        if not self.configuration_parser.has_section(section_name):
                            self.configuration_parser.add_section(section_name)
                            self.profile_string_variable.set(new_profile_name)
                            self.change_active_profile(new_profile_name)
                            self.update_profile_dropdown_list()
                        dialog_window.destroy()
                
                create_button = customtkinter.CTkButton(dialog_window, text="Create", command=save_new_profile_action, fg_color="#27AE60", hover_color="#2ECC71", border_width=1, border_color="#000000")
                create_button.pack(pady=(10, 0))

            def remove_current_profile(self):
                current_profile_name = self.profile_string_variable.get()
                if current_profile_name == "Default":
                    return
                section_name = f"Profile_{current_profile_name}"
                self.configuration_parser.remove_section(section_name)
                self.profile_string_variable.set("Default")
                self.change_active_profile("Default")
                self.update_profile_dropdown_list()

            def add_manual_program(self):
                raw_program_executable_name = self.program_name_entry.get().strip()
                if not raw_program_executable_name:
                    return
                
                program_executable_name = raw_program_executable_name.strip('"\'')
                if program_executable_name.lower().endswith(".exe"):
                    program_executable_name = program_executable_name[:-4]
                
                formatted_key_name = f'"{program_executable_name}"'
                
                focus_priority_level = self.focus_priority_combobox.get()
                unfocus_priority_level = self.unfocus_priority_combobox.get()
                
                current_profile_section = f"Profile_{self.profile_string_variable.get()}"
                self.configuration_parser[current_profile_section][formatted_key_name] = f"{focus_priority_level},{unfocus_priority_level}"
                self.save_configuration_to_file()
                self.program_name_entry.delete(0, "end")
                self.render_programs_list()

            def delete_program(self, program_executable_name):
                current_profile_section = f"Profile_{self.profile_string_variable.get()}"
                formatted_key_name = f'"{program_executable_name}"'
                
                if self.configuration_parser.has_option(current_profile_section, formatted_key_name):
                    self.configuration_parser.remove_option(current_profile_section, formatted_key_name)
                    self.save_configuration_to_file()
                    self.render_programs_list()
                elif self.configuration_parser.has_option(current_profile_section, program_executable_name):
                    self.configuration_parser.remove_option(current_profile_section, program_executable_name)
                    self.save_configuration_to_file()
                    self.render_programs_list()

            def update_program_priority(self, program_executable_name, priority_type, new_priority_value):
                current_profile_section = f"Profile_{self.profile_string_variable.get()}"
                formatted_key_name = f'"{program_executable_name}"'
                
                priorities_string = self.configuration_parser[current_profile_section].get(formatted_key_name, self.configuration_parser[current_profile_section].get(program_executable_name, "High,Normal"))
                focus_priority_level, unfocus_priority_level = priorities_string.split(",")
                
                if priority_type == "focus":
                    focus_priority_level = new_priority_value
                else:
                    unfocus_priority_level = new_priority_value
                    
                self.configuration_parser[current_profile_section][formatted_key_name] = f"{focus_priority_level},{unfocus_priority_level}"
                self.save_configuration_to_file()

            def move_program_position(self, program_executable_name, direction_string):
                current_profile_section = f"Profile_{self.profile_string_variable.get()}"
                if not self.configuration_parser.has_section(current_profile_section):
                    return
                
                items_list = list(self.configuration_parser.items(current_profile_section))
                target_index_number = -1
                for index_number, (key_name, value_string) in enumerate(items_list):
                    if key_name.strip('"\'').lower() == program_executable_name.lower():
                        target_index_number = index_number
                        break
                
                if target_index_number == -1:
                    return
                
                if direction_string == "up" and target_index_number > 0:
                    items_list[target_index_number], items_list[target_index_number - 1] = items_list[target_index_number - 1], items_list[target_index_number]
                elif direction_string == "down" and target_index_number < len(items_list) - 1:
                    items_list[target_index_number], items_list[target_index_number + 1] = items_list[target_index_number + 1], items_list[target_index_number]
                else:
                    return
                
                self.configuration_parser.remove_section(current_profile_section)
                self.configuration_parser.add_section(current_profile_section)
                for key_name, value_string in items_list:
                    self.configuration_parser[current_profile_section][key_name] = value_string
                
                self.save_configuration_to_file()
                self.render_programs_list()

            def open_edit_program_name_dialog(self, old_program_name):
                dialog_window = customtkinter.CTkToplevel(self)
                dialog_window.title("Edit Program Name")
                dialog_window.geometry("350x150")
                dialog_window.resizable(False, False)
                dialog_window.attributes("-topmost", True)
                dialog_window.configure(fg_color="#1E1E1E")
                
                customtkinter.CTkLabel(dialog_window, text="Enter New Program Name:", text_color="#E0E0E0").pack(pady=(15, 5))
                name_entry = customtkinter.CTkEntry(dialog_window, width=280, fg_color="#2A2A2A", border_width=1, border_color="#000000")
                name_entry.insert(0, old_program_name)
                name_entry.pack(pady=5)
                
                def save_renamed_program():
                    new_name = name_entry.get().strip().strip('"\'')
                    if not new_name:
                        dialog_window.destroy()
                        return
                    if new_name.lower().endswith(".exe"):
                        new_name = new_name[:-4]
                    
                    current_profile_section = f"Profile_{self.profile_string_variable.get()}"
                    old_formatted_key = f'"{old_program_name}"'
                    
                    priorities_string = "High,Normal"
                    if self.configuration_parser.has_option(current_profile_section, old_formatted_key):
                        priorities_string = self.configuration_parser[current_profile_section].get(old_formatted_key)
                        self.configuration_parser.remove_option(current_profile_section, old_formatted_key)
                    elif self.configuration_parser.has_option(current_profile_section, old_program_name):
                        priorities_string = self.configuration_parser[current_profile_section].get(old_program_name)
                        self.configuration_parser.remove_option(current_profile_section, old_program_name)
                    
                    new_formatted_key = f'"{new_name}"'
                    self.configuration_parser[current_profile_section][new_formatted_key] = priorities_string
                    self.save_configuration_to_file()
                    self.render_programs_list()
                    dialog_window.destroy()
                
                save_button = customtkinter.CTkButton(dialog_window, text="Save", command=save_renamed_program, fg_color="#27AE60", hover_color="#2ECC71", border_width=1, border_color="#000000")
                save_button.pack(pady=(10, 0))

            def show_context_menu(self, event_object, program_name):
                context_menu = tkinter.Menu(self, tearoff=0, background="#2A2A2A", foreground="#FFFFFF", activebackground="#1F6AA5", activeforeground="#FFFFFF", borderwidth=0, relief="flat")
                context_menu.add_command(label="Edit Name", command=lambda: self.open_edit_program_name_dialog(program_name))
                context_menu.add_command(label="Delete", command=lambda: self.delete_program(program_name))
                try:
                    context_menu.tk_popup(event_object.x_root, event_object.y_root)
                finally:
                    context_menu.grab_release()

            def render_programs_list(self):
                for child_widget in self.programs_scrollable_frame.winfo_children():
                    child_widget.destroy()
                    
                current_profile_section = f"Profile_{self.profile_string_variable.get()}"
                search_query_string = self.search_string_variable.get().lower()
                
                if self.configuration_parser.has_section(current_profile_section):
                    for raw_key_name, priorities_string in self.configuration_parser.items(current_profile_section):
                        clean_program_name = raw_key_name.strip('"\'')
                        if search_query_string in clean_program_name.lower():
                            try:
                                focus_priority_level, unfocus_priority_level = priorities_string.split(",")
                                
                                program_row_frame = customtkinter.CTkFrame(
                                    self.programs_scrollable_frame, 
                                    corner_radius=8, 
                                    border_width=1, 
                                    border_color="#000000",
                                    fg_color="#2A2A2A"
                                )
                                program_row_frame.pack(fill="x", pady=4, padx=2)
                                
                                label_frame = customtkinter.CTkFrame(program_row_frame, fg_color="transparent")
                                label_frame.pack(side="left", fill="x", expand=True, padx=10, pady=10)
                                
                                name_label = customtkinter.CTkLabel(label_frame, text=clean_program_name, font=customtkinter.CTkFont(size=14, weight="bold"), text_color="#64B5F6")
                                name_label.pack(anchor="w")
                                name_label.bind("<Button-3>", lambda event_object, name=clean_program_name: self.show_context_menu(event_object, name))
                                
                                controls_frame = customtkinter.CTkFrame(program_row_frame, fg_color="transparent")
                                controls_frame.pack(side="right", padx=10, pady=10)
                                
                                customtkinter.CTkButton(controls_frame, text="▲", width=30, command=lambda name=clean_program_name: self.move_program_position(name, "up"), fg_color="#3A3A3A", hover_color="#4A4A4A", border_width=1, border_color="#000000").pack(side="left", padx=(0, 2))
                                customtkinter.CTkButton(controls_frame, text="▼", width=30, command=lambda name=clean_program_name: self.move_program_position(name, "down"), fg_color="#3A3A3A", hover_color="#4A4A4A", border_width=1, border_color="#000000").pack(side="left", padx=(0, 10))
                                
                                focus_combobox = customtkinter.CTkComboBox(controls_frame, values=self.priority_levels_list, width=100, command=lambda value, name=clean_program_name: self.update_program_priority(name, "focus", value), fg_color="#1E1E1E", button_color="#3A3A3A", dropdown_fg_color="#2A2A2A", border_width=1, border_color="#000000")
                                focus_combobox._dropdown_menu.configure(relief="flat", borderwidth=0)
                                focus_combobox.set(focus_priority_level)
                                focus_combobox.pack(side="left", padx=(0, 5))
                                
                                unfocus_combobox = customtkinter.CTkComboBox(controls_frame, values=self.priority_levels_list, width=100, command=lambda value, name=clean_program_name: self.update_program_priority(name, "unfocus", value), fg_color="#1E1E1E", button_color="#3A3A3A", dropdown_fg_color="#2A2A2A", border_width=1, border_color="#000000")
                                unfocus_combobox._dropdown_menu.configure(relief="flat", borderwidth=0)
                                unfocus_combobox.set(unfocus_priority_level)
                                unfocus_combobox.pack(side="left")
                                
                            except ValueError:
                                continue

            def fetch_and_add_active_program(self):
                def fetch_process_action():
                    time.sleep(1)
                    active_window_handle = win32gui.GetForegroundWindow()
                    if active_window_handle:
                        thread_identifier, active_process_identifier = win32process.GetWindowThreadProcessId(active_window_handle)
                        try:
                            process_object = psutil.Process(active_process_identifier)
                            raw_executable_name = process_object.name().strip('"\'')
                            if raw_executable_name.lower().endswith(".exe"):
                                raw_executable_name = raw_executable_name[:-4]
                            
                            formatted_key_name = f'"{raw_executable_name}"'
                            focus_priority_level = self.focus_priority_combobox.get()
                            unfocus_priority_level = self.unfocus_priority_combobox.get()
                            
                            current_profile_section = f"Profile_{self.profile_string_variable.get()}"
                            self.configuration_parser[current_profile_section][formatted_key_name] = f"{focus_priority_level},{unfocus_priority_level}"
                            self.save_configuration_to_file()
                            self.after(0, self.render_programs_list)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                threading.Thread(target=fetch_process_action, daemon=True).start()

            def on_delay_settings_change(self):
                focus_value = self.focus_delay_string_variable.get().strip()
                scan_value = self.scan_delay_string_variable.get().strip()
                if focus_value.isdigit():
                    self.configuration_parser["Settings"]["focus_delay_milliseconds"] = focus_value
                if scan_value.isdigit():
                    self.configuration_parser["Settings"]["process_scan_delay_milliseconds"] = scan_value
                self.save_configuration_to_file()

            def toggle_always_on_top(self):
                self.configuration_parser["Settings"]["always_on_top"] = str(self.always_on_top_boolean_variable.get())
                self.save_configuration_to_file()
                self.apply_always_on_top_setting()

            def apply_always_on_top_setting(self):
                self.attributes("-topmost", self.always_on_top_boolean_variable.get())

            def open_source_folder(self):
                source_directory_path = os.path.dirname(os.path.abspath(__file__))
                os.startfile(source_directory_path)

            def create_app_icon(self):
                image = PIL.Image.new("RGB", (64, 64), color=(33, 150, 243))
                draw = PIL.ImageDraw.Draw(image)
                draw.rectangle((16, 16, 48, 48), fill=(255, 255, 255))
                draw.rectangle((24, 24, 40, 40), fill=(33, 150, 243))
                return image

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
                self.tray_icon = pystray.Icon("PriorityManager", image, "Priority Manager", menu)
                threading.Thread(target=self.tray_icon.run, daemon=True).start()

            def hide_to_tray(self):
                self.withdraw()
                self.setup_tray_icon()

            def show_from_tray(self, icon_object=None, item_object=None):
                if self.tray_icon:
                    try:
                        self.tray_icon.stop()
                    except Exception:
                        pass
                    self.tray_icon = None
                self.after(0, self.deiconify)
                self.after(100, self.lift)

            def exit_from_tray(self, icon_object=None, item_object=None):
                self.running_thread_flag = False
                if self.tray_icon:
                    try:
                        self.tray_icon.stop()
                    except Exception:
                        pass
                    self.tray_icon = None
                self.after(0, self.destroy)
                sys.exit(0)

            def close_application_directly(self):
                self.running_thread_flag = False
                if self.tray_icon:
                    try:
                        self.tray_icon.stop()
                    except Exception:
                        pass
                    self.tray_icon = None
                self.destroy()
                sys.exit(0)

            def monitor_system_tray_loop(self):
                while self.running_thread_flag:
                    try:
                        time.sleep(3)
                        if self.tray_icon is not None:
                            pass
                    except Exception:
                        time.sleep(1)

            def manage_process_priorities_loop(self):
                while self.running_thread_flag:
                    try:
                        focus_delay_seconds = int(self.configuration_parser["Settings"].get("focus_delay_milliseconds", "300")) / 1000.0
                        active_profile_name = self.configuration_parser['Settings'].get('active_profile', 'Default')
                        current_profile_section = f"Profile_{active_profile_name}"
                        
                        if not self.configuration_parser.has_section(current_profile_section):
                            time.sleep(focus_delay_seconds)
                            continue

                        active_window_handle = win32gui.GetForegroundWindow()
                        active_executable_name = ""
                        if active_window_handle:
                            thread_identifier, active_process_identifier = win32process.GetWindowThreadProcessId(active_window_handle)
                            try:
                                active_executable_name = psutil.Process(active_process_identifier).name().strip('"\'')
                                if active_executable_name.lower().endswith(".exe"):
                                    active_executable_name = active_executable_name[:-4]
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass

                        configured_programs_dictionary = {}
                        for raw_key_name, priorities_string in self.configuration_parser.items(current_profile_section):
                            clean_program_name = raw_key_name.strip('"\'')
                            try:
                                focus_priority_level, unfocus_priority_level = priorities_string.split(",")
                                configured_programs_dictionary[clean_program_name.lower()] = {
                                    "focus": self.priority_mapping_dictionary.get(focus_priority_level, psutil.NORMAL_PRIORITY_CLASS),
                                    "unfocus": self.priority_mapping_dictionary.get(unfocus_priority_level, psutil.NORMAL_PRIORITY_CLASS)
                                }
                            except ValueError:
                                continue

                        is_configured_focus = active_executable_name.lower() in configured_programs_dictionary
                        self.after(0, lambda name=active_executable_name, flag=is_configured_focus: self.update_current_focus_status_display(name if name else "None", flag))

                        for process_object in psutil.process_iter(['name']):
                            try:
                                clean_process_name = process_object.info['name'].strip('"\'')
                                if clean_process_name.lower().endswith(".exe"):
                                    clean_process_name = clean_process_name[:-4]
                                
                                if clean_process_name.lower() in configured_programs_dictionary:
                                    priority_configuration = configured_programs_dictionary[clean_process_name.lower()]
                                    target_priority = priority_configuration["focus"] if clean_process_name.lower() == active_executable_name.lower() else priority_configuration["unfocus"]
                                    
                                    current_priority = process_object.nice()
                                    if current_priority != target_priority:
                                        process_object.nice(target_priority)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                continue

                        time.sleep(focus_delay_seconds)
                    except Exception:
                        time.sleep(1)

        application_instance = PriorityManagerApplication()
        application_instance.mainloop()

    except Exception as unexpected_exception:
        error_message = traceback.format_exc()
        try:
            console_window_handle = ctypes.windll.kernel32.GetConsoleWindow()
            if console_window_handle != 0:
                ctypes.windll.user32.ShowWindow(console_window_handle, 5)
        except Exception:
            pass
        try:
            pyperclip.copy(error_message)
            print("Error details copied to clipboard.")
        except Exception:
            pass
        print("Critical Error Encountered:\n" + error_message)
        input("Press Enter to close this window...")
