import ctypes
import json
import os
import platform
import re
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import urllib.error
import uuid
from datetime import datetime

def global_exception_handler(exception_type, exception_value, exception_traceback):
    if issubclass(exception_type, SystemExit): 
        sys.__excepthook__(exception_type, exception_value, exception_traceback)
        return
    if platform.system() == "Windows":
        console_window_handle = ctypes.windll.kernel32.GetConsoleWindow()
        if console_window_handle != 0: ctypes.windll.user32.ShowWindow(console_window_handle, 1)
    traceback.print_exception(exception_type, exception_value, exception_traceback)
    input("\nPress Enter to exit...")

sys.excepthook = global_exception_handler

if platform.system() == "Windows" and not ctypes.windll.shell32.IsUserAnAdmin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, '"' + os.path.abspath(sys.argv[0]) + '"', None, 1)
    sys.exit(0)

try:
    import customtkinter
except ImportError:
    if input("Library customtkinter is missing. Do you want to install it? (yes/no): ").lower() in ["yes", "y"]:
        subprocess.run([sys.executable, "-m", "pip", "install", "customtkinter"], check=True)
        import customtkinter
    else: sys.exit(1)

try:
    import requests
except ImportError:
    if input("Library requests is missing. Do you want to install it? (yes/no): ").lower() in ["yes", "y"]:
        subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
        import requests
    else: sys.exit(1)

if platform.system() == "Windows":
    console_window_handle = ctypes.windll.kernel32.GetConsoleWindow()
    if console_window_handle != 0: ctypes.windll.user32.ShowWindow(console_window_handle, 0)

def manage_configuration(write_mode_boolean=False, directory_name_string="results", delete_flag_boolean=False, show_details_information_boolean=False, ffmpeg_executable_path_string=r"D:\.data\Apps\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe", output_image_name_string="Image.png"):
    configuration_path_string = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
    if write_mode_boolean:
        with open(configuration_path_string, "w", encoding="utf-8") as file_handle:
            file_handle.write("ExportDirectory = " + str(directory_name_string) + "\nDeletePreviousResults = " + str(delete_flag_boolean).lower() + "\nShowDetailsInformation = " + str(show_details_information_boolean).lower() + "\nFFmpegExecutablePath = " + str(ffmpeg_executable_path_string) + "\nOutputImageName = " + str(output_image_name_string) + "\n")
        return directory_name_string, delete_flag_boolean, show_details_information_boolean, ffmpeg_executable_path_string, output_image_name_string
    if not os.path.exists(configuration_path_string): return manage_configuration(True)
    with open(configuration_path_string, "r", encoding="utf-8") as file_handle:
        for line_content_string in file_handle:
            if "=" in line_content_string:
                key_string, value_string = [item_string.strip() for item_string in line_content_string.split("=", 1)]
                if key_string.lower() == "exportdirectory": directory_name_string = value_string
                elif key_string.lower() == "deletepreviousresults": delete_flag_boolean = (value_string.lower() == "true")
                elif key_string.lower() == "showdetailsinformation": show_details_information_boolean = (value_string.lower() == "true")
                elif key_string.lower() == "ffmpegexecutablepath": ffmpeg_executable_path_string = value_string
                elif key_string.lower() == "outputimagename": output_image_name_string = value_string
    return directory_name_string, delete_flag_boolean, show_details_information_boolean, ffmpeg_executable_path_string, output_image_name_string

def process_exports(track_list, entity_name_string, entity_description_string, uniform_resource_locator_string, export_directory_path_string, content_type_string, show_details_information_boolean):
    safe_name_string = re.sub(r'[<>:"/\\|?*]', '', entity_name_string).strip().encode("ascii", "ignore").decode("ascii") or "Spotify_Export"
    os.makedirs(export_directory_path_string, exist_ok=True)
    current_time_object = datetime.now().astimezone()
    time_string = current_time_object.strftime("%Y-%m-%d %H:%M:%S") + " Coordinated Universal Time " + current_time_object.strftime("%z")[:3]
    
    generated_files_list = []
    
    if content_type_string in ["playlist", "album", "track"]:
        configurations_list = [
            ("🔗", "➡️", track_list, lambda item_dictionary: item_dictionary["link"]),
            ("🎫", "➡️", track_list, lambda item_dictionary: str(item_dictionary["artist"]) + " - " + str(item_dictionary["name"]))
        ]
        for emoji_string, sort_symbol_string, sorted_tracks_list, format_function in configurations_list:
            file_path_string = os.path.join(export_directory_path_string, emoji_string + " " + safe_name_string + ".txt")
            header_content_string = ""
            if show_details_information_boolean:
                header_content_string = "=" * 80 + "\n| Spotify Export Report\n" + "=" * 80 + "\n"
                header_content_string += "| Title       : " + str(entity_name_string) + "\n| Description : " + str(entity_description_string or "-") + "\n"
                header_content_string += "| Type        : " + str(content_type_string).title() + "\n| Source Link : " + str(uniform_resource_locator_string) + "\n"
                header_content_string += "| Sort Order  : " + str(sort_symbol_string) + "\n| Generated   : " + time_string + "\n" + "=" * 80 + "\n"
            
            with open(file_path_string, "w", encoding="utf-8") as file_handle:
                file_handle.write(header_content_string + "\n".join([format_function(track_item_dictionary) for track_item_dictionary in sorted_tracks_list]))
            generated_files_list.append({"path_string": file_path_string, "real_name_string": entity_name_string, "emoji_string": emoji_string})
            
    elif content_type_string in ["user", "artist"]:
        names_only_file_path_string = os.path.join(export_directory_path_string, "📝 " + safe_name_string + " - Name And Description.txt")
        header_content_string = ""
        if show_details_information_boolean:
            header_content_string = "=" * 80 + "\n| Spotify Export Report\n" + "=" * 80 + "\n"
            header_content_string += "| Title       : " + str(entity_name_string) + "\n| Description : " + str(entity_description_string or "-") + "\n"
            header_content_string += "| Type        : " + str(content_type_string).title() + "\n| Source Link : " + str(uniform_resource_locator_string) + "\n"
            header_content_string += "| Sort Order  : ➡️\n| Generated   : " + time_string + "\n" + "=" * 80 + "\n"
        
        names_only_content_list = []
        full_content_list = []
        
        for item_dictionary in track_list:
            item_name_string = item_dictionary.get("name", "Unknown")
            item_description_string = item_dictionary.get("description", "-")
            item_link_string = item_dictionary.get("link", "")
            names_only_content_list.append("Name: " + item_name_string + "\nDescription: " + item_description_string + "\nLink: " + item_link_string + "\n")
            
            songs_list = item_dictionary.get("tracks", [])
            songs_formatted_string = "\n".join(["  - " + str(song_dictionary.get("artist")) + " - " + str(song_dictionary.get("name")) + " (" + str(song_dictionary.get("link")) + ")" for song_dictionary in songs_list]) if songs_list else "  (No tracks retrieved)"
            full_content_list.append("Name: " + item_name_string + "\nDescription: " + item_description_string + "\nLink: " + item_link_string + "\nTracks:\n" + songs_formatted_string + "\n")
            
        with open(names_only_file_path_string, "w", encoding="utf-8") as file_handle:
            file_handle.write(header_content_string + "\n".join(names_only_content_list))
        generated_files_list.append({"path_string": names_only_file_path_string, "real_name_string": entity_name_string + " - Name And Description", "emoji_string": "📝"})
        
        full_file_path_string = os.path.join(export_directory_path_string, "🎶 " + safe_name_string + " - Name Description And Songs.txt")
        with open(full_file_path_string, "w", encoding="utf-8") as file_handle:
            file_handle.write(header_content_string + "\n".join(full_content_list))
        generated_files_list.append({"path_string": full_file_path_string, "real_name_string": entity_name_string + " - Name Description And Songs", "emoji_string": "🎶"})
        
    return generated_files_list

def extract_image_link_from_spotify(spotify_link_string):
    request_headers_dictionary = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    thumbnail_link_string = None
    oembed_link_string = "https://open.spotify.com/oembed?url=" + str(spotify_link_string) + "&cb=" + str(uuid.uuid4())
    
    try:
        response_object = requests.get(oembed_link_string, headers=request_headers_dictionary, timeout=10)
        if response_object.status_code == 200:
            dictionary_data = response_object.json()
            thumbnail_link_string = dictionary_data.get("thumbnail_url")
    except Exception:
        thumbnail_link_string = None

    if not thumbnail_link_string:
        try:
            page_response_object = requests.get(spotify_link_string, headers=request_headers_dictionary, timeout=10)
            if page_response_object.status_code == 200:
                open_graph_match_object = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', page_response_object.text)
                if open_graph_match_object:
                    thumbnail_link_string = open_graph_match_object.group(1)
                else:
                    twitter_match_object = re.search(r'<meta\s+name="twitter:image"\s+content="([^"]+)"', page_response_object.text)
                    if twitter_match_object:
                        thumbnail_link_string = twitter_match_object.group(1)
        except Exception as exception_object:
            raise Exception("Failed to fetch Spotify page data: " + str(exception_object))

    if not thumbnail_link_string:
        raise Exception("Could not find cover image or avatar uniform resource locator from the provided Spotify link.")

    quality_patterns_list = [
        "ab67616d000082c1",
        "ab6761610000e5eb",
        "ab67706c000082c1",
        "ab67616d00001e02",
        "ab67616100001e02",
        "ab67706c00001e02"
    ]

    for quality_pattern_string in quality_patterns_list:
        test_link_string = re.sub(r'ab67[a-z0-9]{4}0000[a-f0-9]{4}', quality_pattern_string, thumbnail_link_string)
        try:
            check_response_object = requests.head(test_link_string, headers=request_headers_dictionary, timeout=5)
            if check_response_object.status_code == 200:
                return test_link_string
        except Exception:
            continue

    return thumbnail_link_string

def convert_image_to_portable_network_graphics(input_file_path_string, output_file_path_string, ffmpeg_executable_path_string):
    execution_command_list = [
        ffmpeg_executable_path_string,
        "-y",
        "-i", input_file_path_string,
        "-vf", "scale=1000:1000",
        "-c:v", "png",
        "-pred", "mixed",
        output_file_path_string
    ]
    process_result_object = subprocess.run(execution_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process_result_object.returncode != 0:
        raise Exception("Fast Forward Moving Picture Experts Group conversion failed: " + str(process_result_object.stderr.decode("utf-8", errors="ignore")))

class SpotifyExportApplication(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("Spotify Data Fetcher")
        self.geometry(str(950) + "x" + str(450) + "+" + str(int((self.winfo_screenwidth() / 2) - 475)) + "+" + str(int((self.winfo_screenheight() / 2) - 225)))
        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme("blue")
        
        self.emoji_font_family_string = "Segoe UI Emoji" if platform.system() == "Windows" else ("Apple Color Emoji" if platform.system() == "Darwin" else "Noto Color Emoji")
        
        self.export_directory_name_string, self.delete_previous_results_boolean, self.show_details_information_boolean, self.ffmpeg_executable_path_string, self.output_image_name_string = manage_configuration()
        self.export_directory_path_string = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.export_directory_name_string) if self.export_directory_name_string else os.path.dirname(os.path.abspath(__file__))
        
        self.tab_view_widget = customtkinter.CTkTabview(self)
        self.tab_view_widget.pack(fill="both", expand=True, padx=5, pady=5)
        self.dashboard_tab_widget = self.tab_view_widget.add("Dashboard")
        self.settings_tab_widget = self.tab_view_widget.add("Configuration")
        
        self.input_frame_widget = customtkinter.CTkFrame(self.dashboard_tab_widget, fg_color="transparent")
        self.input_frame_widget.pack(fill="x", pady=5)
        self.uniform_resource_locator_entry_widget = customtkinter.CTkEntry(self.input_frame_widget, placeholder_text="Enter Spotify Uniform Resource Locator Here or Press Control V...")
        self.uniform_resource_locator_entry_widget.pack(side="left", fill="x", expand=True, padx=(0, 5))
        for event_sequence_string in ["<Control-v>", "<Command-v>"]: self.uniform_resource_locator_entry_widget.bind(event_sequence_string, lambda event_object: self.after(200, self.start_fetch_thread))
        
        self.paste_and_fetch_image_button_widget = customtkinter.CTkButton(self.input_frame_widget, text="🖼️", width=40, font=customtkinter.CTkFont(family=self.emoji_font_family_string, size=18), command=self.paste_and_fetch_image_automatically)
        self.paste_and_fetch_image_button_widget.pack(side="right", padx=(5, 0))
        
        self.paste_and_fetch_data_button_widget = customtkinter.CTkButton(self.input_frame_widget, text="📋", width=40, font=customtkinter.CTkFont(family=self.emoji_font_family_string, size=18), command=self.paste_and_fetch_data_automatically)
        self.paste_and_fetch_data_button_widget.pack(side="right", padx=(5, 0))
        
        self.middle_frame_widget = customtkinter.CTkFrame(self.dashboard_tab_widget, fg_color="transparent")
        self.middle_frame_widget.pack(fill="both", expand=True, pady=5)
        
        self.log_textbox_widget = customtkinter.CTkTextbox(self.middle_frame_widget, state="disabled", width=400)
        self.log_textbox_widget.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        self.files_scrollable_frame_widget = customtkinter.CTkScrollableFrame(self.middle_frame_widget, label_text="Generated Files", width=450)
        self.files_scrollable_frame_widget.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        self.bottom_frame_widget = customtkinter.CTkFrame(self.dashboard_tab_widget, fg_color="transparent")
        self.bottom_frame_widget.pack(fill="x", pady=5)
        customtkinter.CTkButton(self.bottom_frame_widget, text="Open Results Directory", height=40, command=lambda: self.open_system_path(self.export_directory_path_string)).pack(side="left", fill="x", expand=True, padx=(0, 5))
        customtkinter.CTkButton(self.bottom_frame_widget, text="Open Code Directory", height=40, command=lambda: self.open_system_path(os.path.dirname(os.path.abspath(__file__)))).pack(side="right", fill="x", expand=True, padx=(5, 0))
        
        customtkinter.CTkLabel(self.settings_tab_widget, text="Export Directory Name:").pack(anchor="w", pady=5, padx=5)
        self.export_directory_entry_widget = customtkinter.CTkEntry(self.settings_tab_widget)
        self.export_directory_entry_widget.pack(fill="x", pady=5, padx=5)
        self.export_directory_entry_widget.insert(0, self.export_directory_name_string)
        
        self.delete_previous_results_checkbox_widget = customtkinter.CTkCheckBox(self.settings_tab_widget, text="Delete Previous Results Automatically")
        self.delete_previous_results_checkbox_widget.pack(anchor="w", pady=5, padx=5)
        if self.delete_previous_results_boolean: self.delete_previous_results_checkbox_widget.select()
        
        self.show_details_information_checkbox_widget = customtkinter.CTkCheckBox(self.settings_tab_widget, text="Show Details Information")
        self.show_details_information_checkbox_widget.pack(anchor="w", pady=5, padx=5)
        if self.show_details_information_boolean: self.show_details_information_checkbox_widget.select()
        
        customtkinter.CTkLabel(self.settings_tab_widget, text="Executable Path:").pack(anchor="w", pady=5, padx=5)
        self.ffmpeg_path_entry_widget = customtkinter.CTkEntry(self.settings_tab_widget)
        self.ffmpeg_path_entry_widget.pack(fill="x", pady=5, padx=5)
        self.ffmpeg_path_entry_widget.insert(0, self.ffmpeg_executable_path_string)
        
        customtkinter.CTkButton(self.settings_tab_widget, text="Save Configuration", height=40, command=self.save_current_configuration).pack(anchor="w", padx=5, pady=5)
        
        self.append_log_message("Application started successfully.\nExport Directory: " + self.export_directory_path_string)

    def save_current_configuration(self):
        new_directory_name_string = self.export_directory_entry_widget.get().strip()
        new_ffmpeg_path_string = self.ffmpeg_path_entry_widget.get().strip()
        self.export_directory_entry_widget.delete(0, customtkinter.END); self.export_directory_entry_widget.insert(0, new_directory_name_string)
        self.ffmpeg_path_entry_widget.delete(0, customtkinter.END); self.ffmpeg_path_entry_widget.insert(0, new_ffmpeg_path_string)
        self.export_directory_name_string, self.delete_previous_results_boolean, self.show_details_information_boolean, self.ffmpeg_executable_path_string, self.output_image_name_string = manage_configuration(True, new_directory_name_string, bool(self.delete_previous_results_checkbox_widget.get()), bool(self.show_details_information_checkbox_widget.get()), new_ffmpeg_path_string, self.output_image_name_string)
        self.export_directory_path_string = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.export_directory_name_string) if self.export_directory_name_string else os.path.dirname(os.path.abspath(__file__))
        self.append_log_message("Configuration saved. New Export Directory: " + self.export_directory_path_string)

    def paste_and_fetch_data_automatically(self):
        for widget_item_object in self.files_scrollable_frame_widget.winfo_children():
            widget_item_object.destroy()
        try:
            for file_name_string in os.listdir(self.export_directory_path_string):
                if file_name_string.endswith(".txt"):
                    os.remove(os.path.join(self.export_directory_path_string, file_name_string))
        except Exception:
            pass
        try:
            clipboard_content_string = self.clipboard_get()
            self.uniform_resource_locator_entry_widget.delete(0, customtkinter.END)
            self.uniform_resource_locator_entry_widget.insert(0, clipboard_content_string)
            self.append_log_message("Cleared previous results and pasted uniform resource locator for data fetch.")
            self.start_fetch_thread()
        except Exception as execution_error_message:
            self.uniform_resource_locator_entry_widget.delete(0, customtkinter.END)
            self.append_log_message("Cleared previous results. Clipboard is empty or inaccessible: " + str(execution_error_message))

    def paste_and_fetch_image_automatically(self):
        for widget_item_object in self.files_scrollable_frame_widget.winfo_children():
            widget_item_object.destroy()
        try:
            for file_name_string in os.listdir(self.export_directory_path_string):
                if file_name_string.endswith((".png", ".jpg")):
                    os.remove(os.path.join(self.export_directory_path_string, file_name_string))
        except Exception:
            pass
        try:
            clipboard_content_string = self.clipboard_get()
            self.uniform_resource_locator_entry_widget.delete(0, customtkinter.END)
            self.uniform_resource_locator_entry_widget.insert(0, clipboard_content_string)
            self.append_log_message("Cleared previous results and pasted uniform resource locator for image fetch.")
            self.start_image_fetch_thread()
        except Exception as execution_error_message:
            self.uniform_resource_locator_entry_widget.delete(0, customtkinter.END)
            self.append_log_message("Cleared previous results. Clipboard is empty or inaccessible: " + str(execution_error_message))

    def append_log_message(self, message_string):
        self.log_textbox_widget.configure(state="normal")
        self.log_textbox_widget.insert(customtkinter.END, message_string + "\n")
        self.log_textbox_widget.see(customtkinter.END); self.log_textbox_widget.configure(state="disabled")

    def copy_file_content(self, file_path_string):
        try:
            with open(file_path_string, "r", encoding="utf-8") as file_handle:
                file_content_string = file_handle.read()
                self.clipboard_clear()
                self.clipboard_append(file_content_string)
            self.append_log_message("Copied content of file: " + os.path.basename(file_path_string))
        except Exception as execution_error_message:
            self.append_log_message("Failed to copy file content: " + str(execution_error_message))

    def create_file_item(self, file_path_string, real_name_string, emoji_string):
        item_frame_widget = customtkinter.CTkFrame(self.files_scrollable_frame_widget, fg_color="transparent")
        item_frame_widget.pack(fill="x", pady=5, padx=5)
        customtkinter.CTkLabel(item_frame_widget, text=emoji_string, width=30, font=customtkinter.CTkFont(family=self.emoji_font_family_string, size=16)).pack(side="left", padx=(0, 5))
        customtkinter.CTkLabel(item_frame_widget, text=real_name_string, anchor="w").pack(side="left", fill="x", expand=True, padx=(0, 5))
        customtkinter.CTkButton(item_frame_widget, text="📂", width=30, font=customtkinter.CTkFont(family=self.emoji_font_family_string, size=16), command=lambda: self.open_system_path(file_path_string)).pack(side="right", padx=(5, 0))
        customtkinter.CTkButton(item_frame_widget, text="📋", width=30, font=customtkinter.CTkFont(family=self.emoji_font_family_string, size=16), command=lambda: self.copy_file_content(file_path_string)).pack(side="right", padx=(5, 5))

    def start_fetch_thread(self):
        for widget_item_object in self.files_scrollable_frame_widget.winfo_children(): widget_item_object.destroy()
        input_string = self.uniform_resource_locator_entry_widget.get()
        if not input_string.strip(): return self.append_log_message("Input is empty. Please provide a valid uniform resource locator.")
        threading.Thread(target=self.execute_fetch_process, args=(input_string,), daemon=True).start()

    def start_image_fetch_thread(self):
        for widget_item_object in self.files_scrollable_frame_widget.winfo_children(): widget_item_object.destroy()
        input_string = self.uniform_resource_locator_entry_widget.get()
        if not input_string.strip(): return self.append_log_message("Input is empty. Please provide a valid uniform resource locator.")
        threading.Thread(target=self.execute_image_fetch_process, args=(input_string,), daemon=True).start()

    def safe_api_get(self, application_programming_interface_url_string, access_token_string):
        headers_dictionary = {
            "Authorization": "Bearer " + access_token_string, 
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        for attempt_integer in range(4):
            try:
                time.sleep(0.5 + (attempt_integer * 0.5))
                request_object = urllib.request.Request(application_programming_interface_url_string, headers=headers_dictionary)
                with urllib.request.urlopen(request_object, timeout=15) as response_object:
                    if response_object.status == 200:
                        return json.loads(response_object.read().decode("utf-8"))
            except urllib.error.HTTPError as http_error_object:
                if http_error_object.code == 429:
                    sleep_time_integer = int(http_error_object.headers.get("Retry-After", 3))
                    if sleep_time_integer > 60:
                        self.append_log_message("Rate limited. Wait time is " + str(sleep_time_integer) + " seconds. Aborting request to prevent application freeze.")
                        break
                    self.append_log_message("Rate limited. Waiting " + str(sleep_time_integer) + " seconds before retry.")
                    time.sleep(sleep_time_integer)
                    continue
                else:
                    self.append_log_message("Hypertext transfer protocol error " + str(http_error_object.code) + " fetching application programming interface data.")
                    break
            except Exception as error_object:
                if attempt_integer == 3:
                    self.append_log_message("Application programming interface request failed: " + str(error_object))
                time.sleep(1)
        return None

    def fetch_user_playlists(self, user_identifier_string, access_token_string):
        playlists_list = []
        application_programming_interface_url_string = "https://api.spotify.com/v1/users/" + user_identifier_string + "/playlists?limit=50"
        while application_programming_interface_url_string:
            data_dictionary = self.safe_api_get(application_programming_interface_url_string, access_token_string)
            if not data_dictionary:
                break
            items = data_dictionary.get("items", [])
            for item_dictionary in items:
                if item_dictionary:
                    playlists_list.append({
                        "id": item_dictionary.get("id"),
                        "name": item_dictionary.get("name", "Unknown Playlist"),
                        "description": item_dictionary.get("description", "-"),
                        "link": item_dictionary.get("external_urls", {}).get("spotify", "")
                    })
            application_programming_interface_url_string = data_dictionary.get("next")
        return playlists_list

    def fetch_artist_albums(self, artist_identifier_string, access_token_string):
        albums_list = []
        application_programming_interface_url_string = "https://api.spotify.com/v1/artists/" + artist_identifier_string + "/albums?limit=50"
        seen_album_names_set = set()
        while application_programming_interface_url_string:
            data_dictionary = self.safe_api_get(application_programming_interface_url_string, access_token_string)
            if not data_dictionary:
                break
            items = data_dictionary.get("items", [])
            for item_dictionary in items:
                if item_dictionary:
                    album_name_string = item_dictionary.get("name", "Unknown Album")
                    if album_name_string not in seen_album_names_set:
                        seen_album_names_set.add(album_name_string)
                        albums_list.append({
                            "id": item_dictionary.get("id"),
                            "name": album_name_string,
                            "description": "Album Type: " + str(item_dictionary.get("album_type", "album")).title(),
                            "link": item_dictionary.get("external_urls", {}).get("spotify", "")
                        })
            application_programming_interface_url_string = data_dictionary.get("next")
        return albums_list

    def fetch_playlist_tracks(self, playlist_identifier_string, access_token_string):
        tracks_list = []
        application_programming_interface_url_string = "https://api.spotify.com/v1/playlists/" + playlist_identifier_string + "/tracks?limit=100"
        while application_programming_interface_url_string:
            data_dictionary = self.safe_api_get(application_programming_interface_url_string, access_token_string)
            if not data_dictionary:
                break
            items = data_dictionary.get("items", [])
            for item_dictionary in items:
                if item_dictionary:
                    track_dictionary = item_dictionary.get("track")
                    if track_dictionary and track_dictionary.get("id"):
                        artists_string = ", ".join([artist_dictionary.get("name", "") for artist_dictionary in track_dictionary.get("artists", [])])
                        tracks_list.append({
                            "name": track_dictionary.get("name", "Unknown Title"),
                            "artist": artists_string or "Unknown Artist",
                            "link": track_dictionary.get("external_urls", {}).get("spotify", "https://open.spotify.com/track/" + str(track_dictionary.get("id")))
                        })
            application_programming_interface_url_string = data_dictionary.get("next")
        return tracks_list

    def fetch_album_tracks(self, album_identifier_string, access_token_string):
        tracks_list = []
        application_programming_interface_url_string = "https://api.spotify.com/v1/albums/" + album_identifier_string + "/tracks?limit=50"
        while application_programming_interface_url_string:
            data_dictionary = self.safe_api_get(application_programming_interface_url_string, access_token_string)
            if not data_dictionary:
                break
            items = data_dictionary.get("items", [])
            for item_dictionary in items:
                if item_dictionary and item_dictionary.get("id"):
                    artists_string = ", ".join([artist_dictionary.get("name", "") for artist_dictionary in item_dictionary.get("artists", [])])
                    tracks_list.append({
                        "name": item_dictionary.get("name", "Unknown Title"),
                        "artist": artists_string or "Unknown Artist",
                        "link": item_dictionary.get("external_urls", {}).get("spotify", "https://open.spotify.com/track/" + str(item_dictionary.get("id")))
                    })
            application_programming_interface_url_string = data_dictionary.get("next")
        return tracks_list

    def execute_image_fetch_process(self, input_string):
        try:
            self.append_log_message("Starting image fetch process...")
            if not os.path.exists(self.export_directory_path_string):
                os.makedirs(self.export_directory_path_string, exist_ok=True)
                
            spotify_matches_list = re.findall(r"https://open\.spotify\.com/(playlist|track|album|user|artist|show|episode)/([a-zA-Z0-9]+)", input_string)
            if not spotify_matches_list: 
                return self.append_log_message("No valid Spotify links found in input.")
            
            for resource_type_string, resource_identifier_string in spotify_matches_list:
                uniform_resource_locator_string = "https://open.spotify.com/" + resource_type_string + "/" + resource_identifier_string
                image_link_string = extract_image_link_from_spotify(uniform_resource_locator_string)
                self.append_log_message("Found high quality image link.")
                
                image_response_object = requests.get(image_link_string, timeout=15)
                if image_response_object.status_code != 200:
                    raise Exception("Failed to download image from server. Status code: " + str(image_response_object.status_code))
                
                temporary_image_path_string = os.path.join(self.export_directory_path_string, "temporary_cover.jpg")
                output_image_path_string = os.path.join(self.export_directory_path_string, self.output_image_name_string)
                
                with open(temporary_image_path_string, "wb") as file_handle:
                    file_handle.write(image_response_object.content)
                
                self.append_log_message("Converting image to lossless Portable Network Graphics...")
                convert_image_to_portable_network_graphics(temporary_image_path_string, output_image_path_string, self.ffmpeg_executable_path_string)
                
                if os.path.exists(temporary_image_path_string):
                    os.remove(temporary_image_path_string)
                    
                self.append_log_message("Successfully saved image to: " + output_image_path_string)
                self.create_file_item(output_image_path_string, self.output_image_name_string, "🖼️")
                
        except Exception as execution_error_message:
            self.append_log_message("An error occurred during image fetch: " + str(execution_error_message))

    def fallback_extract_tracks_from_embed(self, resource_type_string, resource_identifier_string, entity_name_string):
        extracted_tracks_list = []
        entity_description_string = ""
        try:
            self.append_log_message("Attempting fallback extraction via embed page...")
            cache_buster = str(uuid.uuid4())
            embed_request_object = urllib.request.Request(
                "https://open.spotify.com/embed/" + resource_type_string + "/" + resource_identifier_string + "?cb=" + cache_buster, 
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36", 
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Cache-Control": "no-cache, no-store, must-revalidate", 
                    "Pragma": "no-cache", 
                    "Expires": "0"
                }
            )
            with urllib.request.urlopen(embed_request_object, timeout=10) as response_object:
                data_structure_search_object = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', response_object.read().decode("utf-8"), re.DOTALL)
            if data_structure_search_object:
                entity_data_dictionary = json.loads(data_structure_search_object.group(1)).get("props", {}).get("pageProps", {}).get("state", {}).get("data", {}).get("entity", {})
                entity_name_string = entity_data_dictionary.get("title") or entity_data_dictionary.get("name") or entity_name_string
                entity_description_string = entity_data_dictionary.get("description", "")
                track_list_data = entity_data_dictionary.get("trackList") or entity_data_dictionary.get("tracks") or entity_data_dictionary.get("items") or []
                for track_item_dictionary in track_list_data:
                    artist_names_list = [artist_item_dictionary.get("name") for artist_item_dictionary in track_item_dictionary.get("artists", []) if artist_item_dictionary.get("name")] if track_item_dictionary.get("artists") else []
                    track_uniform_resource_identifier_string = track_item_dictionary.get("uri", "")
                    extracted_tracks_list.append({
                        "name": track_item_dictionary.get("title") or track_item_dictionary.get("name") or "Unknown Title",
                        "artist": track_item_dictionary.get("subtitle") or (", ".join(artist_names_list) if artist_names_list else "Unknown Artist"),
                        "link": "https://open.spotify.com/track/" + str(track_uniform_resource_identifier_string.split(":")[-1]) if "spotify:track:" in track_uniform_resource_identifier_string else (track_item_dictionary.get("external_urls", {}).get("spotify") or "https://open.spotify.com/track/" + str(track_item_dictionary.get("id") or "UnknownLink"))
                    })
        except Exception as fallback_error_message:
            self.append_log_message("Fallback extraction failed: " + str(fallback_error_message))
        return extracted_tracks_list, entity_name_string, entity_description_string

    def execute_fetch_process(self, input_string):
        try:
            if self.delete_previous_results_boolean:
                self.append_log_message("Deleting previous results before fetching...")
                for file_name_string in os.listdir(self.export_directory_path_string):
                    if file_name_string.endswith(".txt"): os.remove(os.path.join(self.export_directory_path_string, file_name_string))
            
            spotify_matches_list = re.findall(r"https://open\.spotify\.com/(playlist|track|album|user|artist)/([a-zA-Z0-9]+)", input_string)
            if not spotify_matches_list: return self.append_log_message("No valid Spotify links found in input.")

            for resource_type_string, resource_identifier_string in spotify_matches_list:
                uniform_resource_locator_string = "https://open.spotify.com/" + resource_type_string + "/" + resource_identifier_string
                self.append_log_message("Processing: " + uniform_resource_locator_string)
                
                access_token_string = None
                try:
                    cache_buster = str(uuid.uuid4())
                    token_request_object = urllib.request.Request(
                        "https://open.spotify.com/embed/track/4uLU6hMCjMI75M1A2tKUQC?cb=" + cache_buster, 
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36", 
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", 
                            "Cache-Control": "no-cache, no-store, must-revalidate", 
                            "Pragma": "no-cache", 
                            "Expires": "0"
                        }
                    )
                    with urllib.request.urlopen(token_request_object, timeout=10) as token_response_object:
                        hypertext_markup_language_string = token_response_object.read().decode("utf-8")
                        session_match_object = re.search(r'<script id="session" data-testid="session" type="application/json">(.+?)</script>', hypertext_markup_language_string)
                        if session_match_object:
                            access_token_string = json.loads(session_match_object.group(1)).get("accessToken")
                        if not access_token_string:
                            fallback_match_object = re.search(r'"accessToken":"([^"]+)"', hypertext_markup_language_string)
                            if fallback_match_object:
                                access_token_string = fallback_match_object.group(1)
                except Exception:
                    pass
                    
                if not access_token_string:
                    try:
                        cache_buster = str(uuid.uuid4())
                        token_request_object = urllib.request.Request(
                            uniform_resource_locator_string + "?cb=" + cache_buster, 
                            headers={
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", 
                                "Accept": "text/html",
                                "Cache-Control": "no-cache, no-store, must-revalidate",
                                "Pragma": "no-cache",
                                "Expires": "0"
                            }
                        )
                        with urllib.request.urlopen(token_request_object, timeout=10) as token_response_object:
                            hypertext_markup_language_string = token_response_object.read().decode("utf-8")
                            session_match_object = re.search(r'<script id="session" data-testid="session" type="application/json">(.+?)</script>', hypertext_markup_language_string)
                            if session_match_object:
                                access_token_string = json.loads(session_match_object.group(1)).get("accessToken")
                    except Exception:
                        pass
                
                if resource_type_string == "user":
                    entity_name_string = "Spotify User"
                    entity_description_string = ""
                    items_collection_list = []
                    
                    try:
                        profile_request_object = urllib.request.Request("https://api.spotify.com/v1/users/" + resource_identifier_string, headers={"Authorization": "Bearer " + access_token_string, "User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(profile_request_object, timeout=10) as profile_response_object:
                            profile_data_dictionary = json.loads(profile_response_object.read().decode("utf-8"))
                            entity_name_string = profile_data_dictionary.get("display_name") or profile_data_dictionary.get("id") or entity_name_string
                    except Exception:
                        pass
                        
                    user_playlists_list = self.fetch_user_playlists(resource_identifier_string, access_token_string) if access_token_string else []
                    for playlist_dictionary in user_playlists_list:
                        playlist_identifier_string = playlist_dictionary.get("id")
                        playlist_tracks_list = self.fetch_playlist_tracks(playlist_identifier_string, access_token_string) if playlist_identifier_string and access_token_string else []
                        if not playlist_tracks_list and playlist_identifier_string:
                            playlist_tracks_list, _, _ = self.fallback_extract_tracks_from_embed("playlist", playlist_identifier_string, playlist_dictionary.get("name"))
                        items_collection_list.append({
                            "name": playlist_dictionary.get("name"),
                            "description": playlist_dictionary.get("description"),
                            "link": playlist_dictionary.get("link"),
                            "tracks": playlist_tracks_list
                        })
                        
                    if not items_collection_list:
                        self.append_log_message("No items found for " + entity_name_string)
                        continue
                        
                    self.append_log_message("Found " + str(len(items_collection_list)) + " collections for " + entity_name_string + ". Exporting files...")
                    for file_information_dictionary in process_exports(items_collection_list, entity_name_string, entity_description_string, uniform_resource_locator_string, self.export_directory_path_string, resource_type_string, self.show_details_information_boolean):
                        self.create_file_item(file_information_dictionary["path_string"], file_information_dictionary["real_name_string"], file_information_dictionary["emoji_string"])

                elif resource_type_string == "artist":
                    entity_name_string = "Spotify Artist"
                    entity_description_string = ""
                    items_collection_list = []
                    
                    try:
                        artist_profile_request_object = urllib.request.Request("https://api.spotify.com/v1/artists/" + resource_identifier_string, headers={"Authorization": "Bearer " + access_token_string, "User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(artist_profile_request_object, timeout=10) as artist_profile_response_object:
                            artist_profile_data_dictionary = json.loads(artist_profile_response_object.read().decode("utf-8"))
                            entity_name_string = artist_profile_data_dictionary.get("name") or entity_name_string
                    except Exception:
                        pass
                        
                    artist_albums_list = self.fetch_artist_albums(resource_identifier_string, access_token_string) if access_token_string else []
                    for album_dictionary in artist_albums_list:
                        album_identifier_string = album_dictionary.get("id")
                        album_tracks_list = self.fetch_album_tracks(album_identifier_string, access_token_string) if album_identifier_string and access_token_string else []
                        if not album_tracks_list and album_identifier_string:
                            album_tracks_list, _, _ = self.fallback_extract_tracks_from_embed("album", album_identifier_string, album_dictionary.get("name"))
                        items_collection_list.append({
                            "name": album_dictionary.get("name"),
                            "description": album_dictionary.get("description"),
                            "link": album_dictionary.get("link"),
                            "tracks": album_tracks_list
                        })
                        
                    if not items_collection_list:
                        self.append_log_message("No items found for " + entity_name_string)
                        continue
                        
                    self.append_log_message("Found " + str(len(items_collection_list)) + " collections for " + entity_name_string + ". Exporting files...")
                    for file_information_dictionary in process_exports(items_collection_list, entity_name_string, entity_description_string, uniform_resource_locator_string, self.export_directory_path_string, resource_type_string, self.show_details_information_boolean):
                        self.create_file_item(file_information_dictionary["path_string"], file_information_dictionary["real_name_string"], file_information_dictionary["emoji_string"])
                        
                elif resource_type_string == "playlist":
                    entity_name_string = "Spotify Playlist"
                    entity_description_string = ""
                    extracted_tracks_list = []
                    
                    try:
                        playlist_profile_request_object = urllib.request.Request("https://api.spotify.com/v1/playlists/" + resource_identifier_string, headers={"Authorization": "Bearer " + access_token_string, "User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(playlist_profile_request_object, timeout=10) as playlist_profile_response_object:
                            playlist_profile_data_dictionary = json.loads(playlist_profile_response_object.read().decode("utf-8"))
                            entity_name_string = playlist_profile_data_dictionary.get("name") or entity_name_string
                            entity_description_string = playlist_profile_data_dictionary.get("description", "")
                    except Exception:
                        pass
                        
                    extracted_tracks_list = self.fetch_playlist_tracks(resource_identifier_string, access_token_string) if access_token_string else []
                    
                    if not extracted_tracks_list:
                        extracted_tracks_list, entity_name_string, entity_description_string = self.fallback_extract_tracks_from_embed(resource_type_string, resource_identifier_string, entity_name_string)
                        
                    if not extracted_tracks_list:
                        self.append_log_message("No tracks found for " + entity_name_string)
                        continue
                        
                    self.append_log_message("Found " + str(len(extracted_tracks_list)) + " items. Exporting files...")
                    for file_information_dictionary in process_exports(extracted_tracks_list, entity_name_string, entity_description_string, uniform_resource_locator_string, self.export_directory_path_string, resource_type_string, self.show_details_information_boolean):
                        self.create_file_item(file_information_dictionary["path_string"], file_information_dictionary["real_name_string"], file_information_dictionary["emoji_string"])

                elif resource_type_string == "album":
                    entity_name_string = "Spotify Album"
                    entity_description_string = ""
                    extracted_tracks_list = []
                    
                    try:
                        album_profile_request_object = urllib.request.Request("https://api.spotify.com/v1/albums/" + resource_identifier_string, headers={"Authorization": "Bearer " + access_token_string, "User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(album_profile_request_object, timeout=10) as album_profile_response_object:
                            album_profile_data_dictionary = json.loads(album_profile_response_object.read().decode("utf-8"))
                            entity_name_string = album_profile_data_dictionary.get("name") or entity_name_string
                            entity_description_string = "Album Type: " + str(album_profile_data_dictionary.get("album_type", "album")).title()
                    except Exception:
                        pass
                        
                    extracted_tracks_list = self.fetch_album_tracks(resource_identifier_string, access_token_string) if access_token_string else []
                    
                    if not extracted_tracks_list:
                        extracted_tracks_list, entity_name_string, entity_description_string = self.fallback_extract_tracks_from_embed(resource_type_string, resource_identifier_string, entity_name_string)
                        
                    if not extracted_tracks_list:
                        self.append_log_message("No tracks found for " + entity_name_string)
                        continue
                        
                    self.append_log_message("Found " + str(len(extracted_tracks_list)) + " items. Exporting files...")
                    for file_information_dictionary in process_exports(extracted_tracks_list, entity_name_string, entity_description_string, uniform_resource_locator_string, self.export_directory_path_string, resource_type_string, self.show_details_information_boolean):
                        self.create_file_item(file_information_dictionary["path_string"], file_information_dictionary["real_name_string"], file_information_dictionary["emoji_string"])

                else:
                    extracted_tracks_list, entity_name_string, entity_description_string = self.fallback_extract_tracks_from_embed(resource_type_string, resource_identifier_string, "Unknown Spotify Extract")
                    if not extracted_tracks_list:
                        self.append_log_message("No tracks found for " + entity_name_string)
                        continue
                    
                    self.append_log_message("Found " + str(len(extracted_tracks_list)) + " items. Exporting files...")
                    for file_information_dictionary in process_exports(extracted_tracks_list, entity_name_string, entity_description_string, uniform_resource_locator_string, self.export_directory_path_string, resource_type_string, self.show_details_information_boolean):
                        self.create_file_item(file_information_dictionary["path_string"], file_information_dictionary["real_name_string"], file_information_dictionary["emoji_string"])
                    
        except Exception as execution_error_message:
            self.append_log_message("An error occurred: " + str(execution_error_message))

    def open_system_path(self, path_string):
        try:
            if platform.system() == "Windows": os.startfile(path_string)
            elif platform.system() == "Darwin": subprocess.run(["open", path_string], check=False)
            else: subprocess.run(["xdg-open", path_string], check=False)
            self.append_log_message("Opened: " + path_string)
        except Exception as open_error_message: self.append_log_message("Failed to open: " + str(open_error_message))

if __name__ == "__main__":
    SpotifyExportApplication().mainloop()
