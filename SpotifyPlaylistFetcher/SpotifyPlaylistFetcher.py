import ctypes, json, os, platform, re, subprocess, sys, threading, traceback, urllib.request
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

if platform.system() == "Windows":
    console_window_handle = ctypes.windll.kernel32.GetConsoleWindow()
    if console_window_handle != 0: ctypes.windll.user32.ShowWindow(console_window_handle, 0)

def manage_configuration(write_mode_boolean=False, directory_name_string="results", delete_flag_boolean=False, ignore_information_flag_boolean=False):
    configuration_path_string = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
    if write_mode_boolean:
        with open(configuration_path_string, "w", encoding="utf-8") as file_handle:
            file_handle.write("ExportDirectory = " + str(directory_name_string) + "\nDeletePreviousResults = " + str(delete_flag_boolean).lower() + "\nIgnoreInformationWhenCopy = " + str(ignore_information_flag_boolean).lower() + "\n")
        return directory_name_string, delete_flag_boolean, ignore_information_flag_boolean
    if not os.path.exists(configuration_path_string): return manage_configuration(True)
    with open(configuration_path_string, "r", encoding="utf-8") as file_handle:
        for line_content_string in file_handle:
            if "=" in line_content_string:
                key_string, value_string = [item_string.strip() for item_string in line_content_string.split("=", 1)]
                if key_string.lower() == "exportdirectory": directory_name_string = value_string
                elif key_string.lower() == "deletepreviousresults": delete_flag_boolean = (value_string.lower() == "true")
                elif key_string.lower() == "ignoreinformationwhencopy": ignore_information_flag_boolean = (value_string.lower() == "true")
    return directory_name_string, delete_flag_boolean, ignore_information_flag_boolean

def process_exports(track_list, entity_name_string, entity_description_string, uniform_resource_locator_string, export_directory_path_string, content_type_string):
    safe_name_string = re.sub(r'[<>:"/\\|?*]', '', entity_name_string).strip().encode("ascii", "ignore").decode("ascii") or "Spotify_Export"
    os.makedirs(export_directory_path_string, exist_ok=True)
    current_time_object = datetime.now().astimezone()
    time_string = current_time_object.strftime("%Y-%m-%d %H:%M:%S") + " UTC" + current_time_object.strftime("%z")[:3]
    
    generated_files_list = []
    
    if content_type_string in ["playlist", "album", "track"]:
        configurations_list = [
            ("🔗", "➡️", track_list, lambda item_dictionary: item_dictionary["link"]),
            ("🎫", "➡️", track_list, lambda item_dictionary: str(item_dictionary["artist"]) + " - " + str(item_dictionary["name"]))
        ]
        for emoji_string, sort_symbol_string, sorted_tracks_list, format_function in configurations_list:
            file_path_string = os.path.join(export_directory_path_string, emoji_string + " " + safe_name_string + ".txt")
            header_content_string = "=" * 80 + "\n| Spotify Export Report\n" + "=" * 80 + "\n"
            header_content_string += "| Title       : " + str(entity_name_string) + "\n| Description : " + str(entity_description_string or "-") + "\n"
            header_content_string += "| Type        : " + str(content_type_string).title() + "\n| Source Link : " + str(uniform_resource_locator_string) + "\n"
            header_content_string += "| Sort Order  : " + str(sort_symbol_string) + "\n| Generated   : " + time_string + "\n" + "=" * 80 + "\n"
            
            with open(file_path_string, "w", encoding="utf-8") as file_handle:
                file_handle.write(header_content_string + "\n".join([format_function(track_item_dictionary) for track_item_dictionary in sorted_tracks_list]))
            generated_files_list.append({"path_string": file_path_string, "real_name_string": entity_name_string, "emoji_string": emoji_string})
            
    elif content_type_string in ["user", "artist"]:
        names_only_file_path_string = os.path.join(export_directory_path_string, "📝 " + safe_name_string + " - Name And Description.txt")
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

class SpotifyExportApplication(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("Spotify Data Fetcher")
        self.geometry(str(950) + "x" + str(450) + "+" + str(int((self.winfo_screenwidth() / 2) - 475)) + "+" + str(int((self.winfo_screenheight() / 2) - 225)))
        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme("blue")
        
        self.emoji_font_family_string = "Segoe UI Emoji" if platform.system() == "Windows" else ("Apple Color Emoji" if platform.system() == "Darwin" else "Noto Color Emoji")
        
        self.export_directory_name_string, self.delete_previous_results_boolean, self.ignore_information_when_copy_boolean = manage_configuration()
        self.export_directory_path_string = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.export_directory_name_string) if self.export_directory_name_string else os.path.dirname(os.path.abspath(__file__))
        
        self.tab_view_widget = customtkinter.CTkTabview(self)
        self.tab_view_widget.pack(fill="both", expand=True, padx=5, pady=5)
        self.dashboard_tab_widget = self.tab_view_widget.add("Dashboard")
        self.settings_tab_widget = self.tab_view_widget.add("Configuration")
        
        self.input_frame_widget = customtkinter.CTkFrame(self.dashboard_tab_widget, fg_color="transparent")
        self.input_frame_widget.pack(fill="x", pady=5)
        self.uniform_resource_locator_entry_widget = customtkinter.CTkEntry(self.input_frame_widget, placeholder_text="Enter Spotify Uniform Resource Locator Here or Press Ctrl+V...")
        self.uniform_resource_locator_entry_widget.pack(side="left", fill="x", expand=True, padx=(0, 5))
        for event_sequence_string in ["<Control-v>", "<Command-v>"]: self.uniform_resource_locator_entry_widget.bind(event_sequence_string, lambda event_object: self.after(200, self.start_fetch_thread))
        customtkinter.CTkButton(self.input_frame_widget, text="📋", width=40, font=customtkinter.CTkFont(family=self.emoji_font_family_string, size=18), command=self.paste_and_fetch_automatically).pack(side="right")
        
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
        
        self.ignore_information_when_copy_checkbox_widget = customtkinter.CTkCheckBox(self.settings_tab_widget, text="Ignore Information When Copy")
        self.ignore_information_when_copy_checkbox_widget.pack(anchor="w", pady=5, padx=5)
        if self.ignore_information_when_copy_boolean: self.ignore_information_when_copy_checkbox_widget.select()
        
        customtkinter.CTkButton(self.settings_tab_widget, text="Save Configuration", height=40, command=self.save_current_configuration).pack(anchor="w", padx=5, pady=5)
        
        self.append_log_message("Application started successfully.\nExport Directory: " + self.export_directory_path_string)

    def save_current_configuration(self):
        new_directory_name_string = self.export_directory_entry_widget.get().strip()
        self.export_directory_entry_widget.delete(0, customtkinter.END); self.export_directory_entry_widget.insert(0, new_directory_name_string)
        self.export_directory_name_string, self.delete_previous_results_boolean, self.ignore_information_when_copy_boolean = manage_configuration(True, new_directory_name_string, bool(self.delete_previous_results_checkbox_widget.get()), bool(self.ignore_information_when_copy_checkbox_widget.get()))
        self.export_directory_path_string = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.export_directory_name_string) if self.export_directory_name_string else os.path.dirname(os.path.abspath(__file__))
        self.append_log_message("Configuration saved. New Export Directory: " + self.export_directory_path_string)

    def paste_and_fetch_automatically(self):
        try:
            self.uniform_resource_locator_entry_widget.delete(0, customtkinter.END)
            self.uniform_resource_locator_entry_widget.insert(0, self.clipboard_get())
            self.append_log_message("Pasted uniform resource locator from clipboard.")
            self.start_fetch_thread()
        except Exception as execution_error_message: self.append_log_message("Failed to read clipboard: " + str(execution_error_message))

    def append_log_message(self, message_string):
        self.log_textbox_widget.configure(state="normal")
        self.log_textbox_widget.insert(customtkinter.END, message_string + "\n")
        self.log_textbox_widget.see(customtkinter.END); self.log_textbox_widget.configure(state="disabled")

    def copy_file_content(self, file_path_string):
        try:
            with open(file_path_string, "r", encoding="utf-8") as file_handle:
                file_content_string = file_handle.read()
                if self.ignore_information_when_copy_boolean:
                    separated_content_list = file_content_string.split("=" * 80 + "\n")
                    if len(separated_content_list) >= 3: file_content_string = separated_content_list[-1].lstrip("\n")
                self.clipboard_clear()
                self.clipboard_append(file_content_string)
            self.append_log_message("Copied content of: " + os.path.basename(file_path_string))
        except Exception as execution_error_message: self.append_log_message("Failed to copy file content: " + str(execution_error_message))

    def create_file_item(self, file_path_string, real_name_string, emoji_string):
        item_frame_widget = customtkinter.CTkFrame(self.files_scrollable_frame_widget, fg_color="transparent")
        item_frame_widget.pack(fill="x", pady=5, padx=5)
        customtkinter.CTkLabel(item_frame_widget, text=emoji_string, width=30, font=customtkinter.CTkFont(family=self.emoji_font_family_string, size=16)).pack(side="left", padx=(0, 5))
        customtkinter.CTkLabel(item_frame_widget, text=real_name_string, anchor="w").pack(side="left", fill="x", expand=True, padx=(0, 5))
        customtkinter.CTkButton(item_frame_widget, text="📂", width=30, font=customtkinter.CTkFont(family=self.emoji_font_family_string, size=16), command=lambda: self.open_system_path(file_path_string)).pack(side="right", padx=(5, 0))
        customtkinter.CTkButton(item_frame_widget, text="📋", width=30, font=customtkinter.CTkFont(family=self.emoji_font_family_string, size=16), command=lambda: self.copy_file_content(file_path_string)).pack(side="right", padx=(5, 5))

    def start_fetch_thread(self):
        input_string = self.uniform_resource_locator_entry_widget.get()
        if not input_string.strip(): return self.append_log_message("Input is empty. Please provide a valid uniform resource locator.")
        for widget_item_object in self.files_scrollable_frame_widget.winfo_children(): widget_item_object.destroy()
        threading.Thread(target=self.execute_fetch_process, args=(input_string,), daemon=True).start()

    def fetch_playlist_tracks(self, playlist_identifier_string, access_token_string):
        tracks_list = []
        application_programming_interface_url_string = "https://api.spotify.com/v1/playlists/" + playlist_identifier_string + "/tracks?limit=100"
        while application_programming_interface_url_string:
            try:
                request_object = urllib.request.Request(application_programming_interface_url_string, headers={"Authorization": "Bearer " + access_token_string, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                with urllib.request.urlopen(request_object, timeout=10) as response_object:
                    data_dictionary = json.loads(response_object.read().decode("utf-8"))
                    for item_dictionary in data_dictionary.get("items", []):
                        track_dictionary = item_dictionary.get("track")
                        if track_dictionary:
                            artists_string = ", ".join([artist_dictionary.get("name", "") for artist_dictionary in track_dictionary.get("artists", [])])
                            tracks_list.append({
                                "name": track_dictionary.get("name", "Unknown Title"),
                                "artist": artists_string or "Unknown Artist",
                                "link": track_dictionary.get("external_urls", {}).get("spotify", "")
                            })
                    application_programming_interface_url_string = data_dictionary.get("next")
            except Exception:
                break
        return tracks_list

    def fetch_album_tracks(self, album_identifier_string, access_token_string):
        tracks_list = []
        application_programming_interface_url_string = "https://api.spotify.com/v1/albums/" + album_identifier_string + "/tracks?limit=50"
        while application_programming_interface_url_string:
            try:
                request_object = urllib.request.Request(application_programming_interface_url_string, headers={"Authorization": "Bearer " + access_token_string, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                with urllib.request.urlopen(request_object, timeout=10) as response_object:
                    data_dictionary = json.loads(response_object.read().decode("utf-8"))
                    for item_dictionary in data_dictionary.get("items", []):
                        artists_string = ", ".join([artist_dictionary.get("name", "") for artist_dictionary in item_dictionary.get("artists", [])])
                        tracks_list.append({
                            "name": item_dictionary.get("name", "Unknown Title"),
                            "artist": artists_string or "Unknown Artist",
                            "link": item_dictionary.get("external_urls", {}).get("spotify", "")
                        })
                    application_programming_interface_url_string = data_dictionary.get("next")
            except Exception:
                break
        return tracks_list

    def execute_fetch_process(self, input_string):
        try:
            if self.delete_previous_results_boolean:
                self.append_log_message("Deleting previous results before fetching...")
                for file_name_string in os.listdir(self.export_directory_path_string):
                    if file_name_string.endswith(".txt"): os.remove(os.path.join(self.export_directory_path_string, file_name_string))
            
            spotify_matches_list = re.findall(r"https://open\.spotify\.com/(playlist|track|album|user|artist)/([a-zA-Z0-9]+)", input_string)
            if not spotify_matches_list: return self.append_log_message("No valid Spotify links found in input.")
            
            access_token_string = None
            try:
                token_request_object = urllib.request.Request("https://open.spotify.com/embed/track/4uLU6hMCjMI75M1A2tKUQC", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36", "Accept": "text/html"})
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

            for resource_type_string, resource_identifier_string in spotify_matches_list:
                uniform_resource_locator_string = "https://open.spotify.com/" + resource_type_string + "/" + resource_identifier_string
                self.append_log_message("Processing: " + uniform_resource_locator_string)
                
                if resource_type_string == "user":
                    entity_name_string = "Spotify User"
                    entity_description_string = ""
                    items_collection_list = []
                    try:
                        user_page_request_object = urllib.request.Request(uniform_resource_locator_string, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36", "Accept-Language": "en-US"})
                        with urllib.request.urlopen(user_page_request_object, timeout=10) as user_response_object:
                            user_html_string = user_response_object.read().decode("utf-8")
                        user_data_match_object = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', user_html_string, re.DOTALL)
                        if user_data_match_object:
                            user_json_data = json.loads(user_data_match_object.group(1))
                            entity_data_dictionary = user_json_data.get("props", {}).get("pageProps", {}).get("state", {}).get("data", {})
                            entity_name_string = entity_data_dictionary.get("name") or entity_data_dictionary.get("displayName") or entity_name_string
                            
                            playlists_items_list = []
                            def find_playlists_recursive(current_node):
                                if isinstance(current_node, dict):
                                    if current_node.get("type") == "playlist" or ("uri" in current_node and "playlist" in str(current_node.get("uri"))):
                                        playlists_items_list.append(current_node)
                                    for key_name, value_content in current_node.items():
                                        find_playlists_recursive(value_content)
                                elif isinstance(current_node, list):
                                    for element_item in current_node:
                                        find_playlists_recursive(element_item)
                            
                            find_playlists_recursive(entity_data_dictionary)
                            
                            for playlist_item_dictionary in playlists_items_list:
                                playlist_id_string = ""
                                playlist_uri_string = playlist_item_dictionary.get("uri", "")
                                if "spotify:playlist:" in playlist_uri_string:
                                    playlist_id_string = playlist_uri_string.split(":")[-1]
                                elif "id" in playlist_item_dictionary:
                                    playlist_id_string = playlist_item_dictionary.get("id")
                                
                                playlist_tracks_list = self.fetch_playlist_tracks(playlist_id_string, access_token_string) if playlist_id_string and access_token_string else []
                                items_collection_list.append({
                                    "name": playlist_item_dictionary.get("name") or playlist_item_dictionary.get("title") or "Unknown Playlist",
                                    "description": playlist_item_dictionary.get("description", "-"),
                                    "link": "https://open.spotify.com/playlist/" + playlist_id_string if playlist_id_string else playlist_item_dictionary.get("external_urls", {}).get("spotify", ""),
                                    "tracks": playlist_tracks_list
                                })
                    except Exception as user_scraping_error_message:
                        self.append_log_message("Error scraping user page: " + str(user_scraping_error_message))
                        
                    if not items_collection_list:
                        self.append_log_message("No items found for " + entity_name_string)
                        continue
                        
                    self.append_log_message("Found " + str(len(items_collection_list)) + " collections for " + entity_name_string + ". Exporting files...")
                    for file_information_dictionary in process_exports(items_collection_list, entity_name_string, entity_description_string, uniform_resource_locator_string, self.export_directory_path_string, resource_type_string):
                        self.create_file_item(file_information_dictionary["path_string"], file_information_dictionary["real_name_string"], file_information_dictionary["emoji_string"])

                elif resource_type_string == "artist":
                    entity_name_string = "Spotify Artist"
                    entity_description_string = ""
                    items_collection_list = []
                    try:
                        artist_page_request_object = urllib.request.Request(uniform_resource_locator_string, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36", "Accept-Language": "en-US"})
                        with urllib.request.urlopen(artist_page_request_object, timeout=10) as artist_response_object:
                            artist_html_string = artist_response_object.read().decode("utf-8")
                        artist_data_match_object = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', artist_html_string, re.DOTALL)
                        if artist_data_match_object:
                            artist_json_data = json.loads(artist_data_match_object.group(1))
                            entity_data_dictionary = artist_json_data.get("props", {}).get("pageProps", {}).get("state", {}).get("data", {})
                            entity_name_string = entity_data_dictionary.get("name") or entity_name_string
                            
                            albums_items_list = []
                            def find_albums_recursive(current_node):
                                if isinstance(current_node, dict):
                                    if current_node.get("type") == "album" or ("uri" in current_node and "album" in str(current_node.get("uri"))):
                                        albums_items_list.append(current_node)
                                    for key_name, value_content in current_node.items():
                                        find_albums_recursive(value_content)
                                elif isinstance(current_node, list):
                                    for element_item in current_node:
                                        find_albums_recursive(element_item)
                                        
                            find_albums_recursive(entity_data_dictionary)
                            
                            seen_album_identifiers_set = set()
                            for album_item_dictionary in albums_items_list:
                                album_id_string = ""
                                album_uri_string = album_item_dictionary.get("uri", "")
                                if "spotify:album:" in album_uri_string:
                                    album_id_string = album_uri_string.split(":")[-1]
                                elif "id" in album_item_dictionary:
                                    album_id_string = album_item_dictionary.get("id")
                                    
                                if album_id_string and album_id_string not in seen_album_identifiers_set:
                                    seen_album_identifiers_set.add(album_id_string)
                                    album_tracks_list = self.fetch_album_tracks(album_id_string, access_token_string) if access_token_string else []
                                    items_collection_list.append({
                                        "name": album_item_dictionary.get("name") or album_item_dictionary.get("title") or "Unknown Album",
                                        "description": "Album Type: " + str(album_item_dictionary.get("album_type", "album")).title(),
                                        "link": "https://open.spotify.com/album/" + album_id_string if album_id_string else album_item_dictionary.get("external_urls", {}).get("spotify", ""),
                                        "tracks": album_tracks_list
                                    })
                    except Exception as artist_scraping_error_message:
                        self.append_log_message("Error scraping artist page: " + str(artist_scraping_error_message))
                        
                    if not items_collection_list:
                        self.append_log_message("No items found for " + entity_name_string)
                        continue
                        
                    self.append_log_message("Found " + str(len(items_collection_list)) + " collections for " + entity_name_string + ". Exporting files...")
                    for file_information_dictionary in process_exports(items_collection_list, entity_name_string, entity_description_string, uniform_resource_locator_string, self.export_directory_path_string, resource_type_string):
                        self.create_file_item(file_information_dictionary["path_string"], file_information_dictionary["real_name_string"], file_information_dictionary["emoji_string"])
                        
                else:
                    try:
                        with urllib.request.urlopen(urllib.request.Request("https://open.spotify.com/embed/" + resource_type_string + "/" + resource_identifier_string, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept-Language": "en-US"}), timeout=10) as response_object:
                            data_structure_search_object = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', response_object.read().decode("utf-8"), re.DOTALL)
                        if not data_structure_search_object: raise ValueError("Could not extract metadata from embed page")
                        
                        entity_data_dictionary = json.loads(data_structure_search_object.group(1)).get("props", {}).get("pageProps", {}).get("state", {}).get("data", {}).get("entity", {})
                        entity_name_string = entity_data_dictionary.get("title") or entity_data_dictionary.get("name") or "Unknown Spotify Extract"
                        entity_description_string = entity_data_dictionary.get("description", "")
                        track_list_data = entity_data_dictionary.get("trackList") or entity_data_dictionary.get("tracks") or entity_data_dictionary.get("items") or []
                        
                        if not track_list_data:
                            self.append_log_message("No tracks found for " + entity_name_string)
                            continue
                        
                        self.append_log_message("Found " + str(len(track_list_data)) + " items. Exporting files...")
                        extracted_tracks_list = []
                        for track_item_dictionary in track_list_data:
                            artist_names_list = [artist_item_dictionary.get("name") for artist_item_dictionary in track_item_dictionary.get("artists", []) if artist_item_dictionary.get("name")] if track_item_dictionary.get("artists") else []
                            track_uniform_resource_identifier_string = track_item_dictionary.get("uri", "")
                            extracted_tracks_list.append({
                                "name": track_item_dictionary.get("title") or track_item_dictionary.get("name") or "Unknown Title",
                                "artist": track_item_dictionary.get("subtitle") or (", ".join(artist_names_list) if artist_names_list else "Unknown Artist"),
                                "link": "https://open.spotify.com/track/" + str(track_uniform_resource_identifier_string.split(":")[-1]) if "spotify:track:" in track_uniform_resource_identifier_string else (track_item_dictionary.get("external_urls", {}).get("spotify") or "https://open.spotify.com/track/" + str(track_item_dictionary.get("id") or "UnknownLink"))
                            })
                        
                        for file_information_dictionary in process_exports(extracted_tracks_list, entity_name_string, entity_description_string, uniform_resource_locator_string, self.export_directory_path_string, resource_type_string):
                            self.create_file_item(file_information_dictionary["path_string"], file_information_dictionary["real_name_string"], file_information_dictionary["emoji_string"])

                    except Exception as loop_execution_error_message:
                        self.append_log_message("Error processing " + uniform_resource_locator_string + ": " + str(loop_execution_error_message))
                    
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
