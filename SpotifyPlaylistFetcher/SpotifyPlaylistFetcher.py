import sys
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
import traceback

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "spotipy"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth

BASE_DIR = Path(__file__).parent.resolve()
EXPORT_DIR = BASE_DIR / "exports"
KEY_FILE = BASE_DIR / "spotify_keys.txt"
CACHE_FILE = BASE_DIR / ".cache"
# CHANGED: Added CONFIG_FILE path
CONFIG_FILE = BASE_DIR / "config.txt"

EXPORT_DIR.mkdir(exist_ok=True)

# CHANGED: Added default configuration template
DEFAULT_CONFIG = """# Configuration File
# Use this file to enable or disable specific export types.
# Format: setting_name = true
# Options are: true or false

# Playlist Export Options
playlist_links_newest = true
playlist_links_oldest = true
playlist_links_original = true

# User/Artist Export Options
overview_file = true
details_full_file = true
details_with_links_file = true
links_newest_file = true
links_oldest_file = true
"""

def load_credentials():
    if not KEY_FILE.exists():
        print("[ERROR] Credentials file missing.")
        KEY_FILE.write_text("CLIENT_ID = \nCLIENT_SECRET = ", encoding="utf-8")
        sys.exit()

    creds = {}
    for line in KEY_FILE.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, val = line.split("=", 1)
            creds[key.strip()] = val.strip()
            
    if not creds.get("CLIENT_ID") or not creds.get("CLIENT_SECRET"):
        print("[ERROR] Client ID or Secret missing in file.")
        sys.exit()
    return creds["CLIENT_ID"], creds["CLIENT_SECRET"]

# CHANGED: Added function to load and parse config.txt
def load_config():
    # Create config file if it doesn't exist
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(DEFAULT_CONFIG, encoding="utf-8")
        print(f"[INFO] Created default config file at {CONFIG_FILE}")

    # Default values
    config = {
        "playlist_links_newest": True,
        "playlist_links_oldest": True,
        "playlist_links_original": True,
        "overview_file": True,
        "details_full_file": True,
        "details_with_links_file": True,
        "links_newest_file": True,
        "links_oldest_file": True,
    }

    try:
        # Read and parse config file
        for line in CONFIG_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().lower()
                if val == "true":
                    config[key] = True
                elif val == "false":
                    config[key] = False
    except Exception as e:
        print(f"[WARN] Could not read config file, using defaults. Error: {e}")

    return config

def clean_name(name):
    if not name:
        return ""
    # Remove invalid filesystem characters
    name = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    # Remove non-ASCII characters (including emojis)
    name = name.encode("ascii", "ignore").decode("ascii")
    return name.strip()

def get_timestamp():
    t = datetime.now().astimezone()
    offset = t.strftime("%z")
    return f"{t.strftime('%d %B %Y %H:%M:%S')} UTC{offset[:3]}"

def format_duration(ms):
    seconds = ms // 1000
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"

def build_header(title, url=None, sort=None):
    line = "=" * 80
    header = f"{line}\n"
    header += f"TITLE: {title}\n"
    header += f"{line}\n"
    
    if url:
        header += f"SOURCE     : {url}\n"
    if sort:
        header += f"ORDER      : {sort}\n"
    header += f"GENERATED  : {get_timestamp()}\n"
    header += f"{line}\n\n"
    return header

def build_section_header(text):
    safe_text = clean_name(text)
    return f"\n{'=' * 80}\n{safe_text.upper()}\n{'=' * 80}\n"

def fetch_playlist_tracks(sp, playlist_id):
    tracks = []
    results = sp.playlist_items(playlist_id)
    while results:
        for item in results.get("items", []):
            track = item.get("track")
            if track:
                artists = ", ".join([a["name"] for a in track.get("artists", [])])
                tracks.append({
                    "name": track["name"],
                    "artist": artists,
                    "album": track.get("album", {}).get("name", ""),
                    "link": track["external_urls"]["spotify"],
                    "date": track.get("album", {}).get("release_date", "0000"),
                    "duration": format_duration(track.get("duration_ms", 0))
                })
        results = sp.next(results) if results.get("next") else None
        time.sleep(0.2)
    return tracks

def fetch_album_tracks(sp, album_id, album_date, album_name):
    tracks = []
    results = sp.album_tracks(album_id)
    while results:
        for item in results.get("items", []):
            artists = ", ".join([a["name"] for a in item.get("artists", [])])
            tracks.append({
                "name": item["name"],
                "artist": artists,
                "album": album_name,
                "link": item["external_urls"]["spotify"],
                "date": album_date,
                "duration": format_duration(item.get("duration_ms", 0)),
                "track_number": item.get("track_number", 0)
            })
        results = sp.next(results) if results.get("next") else None
        time.sleep(0.2)
    return tracks

def write_content(filepath, content):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

def export_playlist(sp, pid, session_dir, config):
    print(f"\n[PROCESS] Fetching playlist data...")
    try:
        metadata = sp.playlist(pid)
    except Exception as e:
        print(f"[ERROR] Could not fetch playlist details: {e}")
        return

    name = clean_name(metadata["name"])
    url = metadata["external_urls"]["spotify"]
    tracks = fetch_playlist_tracks(sp, pid)

    new_old = sorted(tracks, key=lambda x: x["date"], reverse=True)
    old_new = sorted(tracks, key=lambda x: x["date"], reverse=False)
    original = tracks

    print(f"[WRITE] Creating export files for: {name}")

    # CHANGED: Added config checks for playlist exports
    if config.get("playlist_links_newest"):
        content_new = build_header(name, url, "NEWEST TO OLDEST")
        content_new += "\n".join([t['link'] for t in new_old])
        write_content(session_dir / f"{name} - Links Newest to Oldest.txt", content_new)

    if config.get("playlist_links_oldest"):
        content_old = build_header(name, url, "OLDEST TO NEWEST")
        content_old += "\n".join([t['link'] for t in old_new])
        write_content(session_dir / f"{name} - Links Oldest to Newest.txt", content_old)

    if config.get("playlist_links_original"):
        content_orig = build_header(name, url, "ORIGINAL PLAYLIST ORDER")
        content_orig += "\n".join([t['link'] for t in original])
        write_content(session_dir / f"{name} - Links Original Order.txt", content_orig)

def export_user(sp, uid, session_dir, config):
    print(f"\n[PROCESS] Fetching user profile data...")
    try:
        user_meta = sp.user(uid)
    except Exception as e:
        print(f"[ERROR] Could not fetch user profile: {e}")
        return

    user_name = clean_name(user_meta.get("display_name") or uid)
    
    playlists = []
    results = sp.user_playlists(uid)
    while results:
        playlists.extend(results["items"])
        if results['next']:
            results = sp.next(results)
            time.sleep(0.2)
        else:
            results = None

    overview_lines = []
    details_orig = []
    links_orig = []
    links_new = []
    links_old = []

    print(f"[PROCESS] Found {len(playlists)} playlists. Processing...")

    for i, pl in enumerate(playlists, 1):
        try:
            pl_name = clean_name(pl["name"])
            if not pl_name:
                pl_name = f"Playlist {i}"
                
            pl_url = pl["external_urls"]["spotify"]
            pl_desc = pl.get("description") or "No description"
            pl_desc = clean_name(pl_desc)
            pl_count = pl.get("tracks", {}).get("total", 0)
            
            block = f"\nPlaylist   : {pl_name}\nLink       : {pl_url}\nTracks     : {pl_count}\nDescription: {pl_desc}\n"
            overview_lines.append(block)

            tracks = fetch_playlist_tracks(sp, pl["id"])
            
            tracks_new = sorted(tracks, key=lambda x: x["date"], reverse=True)
            tracks_old = sorted(tracks, key=lambda x: x["date"], reverse=False)

            sec_header = f"{pl_name} ({pl_count} Tracks)"
            
            details_header = build_section_header(sec_header)
            detail_lines = []
            for idx, t in enumerate(tracks, 1):
                safe_track_name = clean_name(t['name'])
                safe_artist_name = clean_name(t['artist'])
                safe_album_name = clean_name(t['album'])
                detail_lines.append(f"{idx:02}. {safe_artist_name} – {safe_track_name} ({safe_album_name}) [{t['duration']}]")
            details_orig.append(details_header + "\n".join(detail_lines))

            link_header = build_section_header(sec_header)
            links_orig.append(link_header + "\n".join([t['link'] for t in tracks]))

            link_header_new = build_section_header(f"{sec_header} [Sorted New]")
            links_new.append(link_header_new + "\n".join([t['link'] for t in tracks_new]))

            link_header_old = build_section_header(f"{sec_header} [Sorted Old]")
            links_old.append(link_header_old + "\n".join([t['link'] for t in tracks_old]))
            
            print(f"  [OK] Processed {i}/{len(playlists)}: {pl_name}")
        except Exception as e:
            print(f"  [ERROR] Failed to process playlist {i} ({pl_name}): {e}")
            continue

    header_block = build_header(f"{user_name} Export")
    
    print(f"[WRITE] Creating export files for: {user_name}")
    
    # CHANGED: Added config checks for user exports
    if config.get("overview_file"):
        write_content(session_dir / f"{user_name} - Overview.txt", header_block + "\n".join(overview_lines))
    if config.get("details_full_file"):
        write_content(session_dir / f"{user_name} - Full Details.txt", header_block + "\n".join(details_orig))
    if config.get("details_with_links_file"):
        write_content(session_dir / f"{user_name} - Full Details with Links.txt", header_block + "\n".join(links_orig))
    if config.get("links_newest_file"):
        write_content(session_dir / f"{user_name} - Links Newest to Oldest.txt", header_block + "\n".join(links_new))
    if config.get("links_oldest_file"):
        write_content(session_dir / f"{user_name} - Links Oldest to Newest.txt", header_block + "\n".join(links_old))

def export_artist(sp, aid, session_dir, config):
    print(f"\n[PROCESS] Fetching artist data...")
    try:
        artist_meta = sp.artist(aid)
    except Exception as e:
        print(f"[ERROR] Could not fetch artist profile: {e}")
        return
        
    artist_name = clean_name(artist_meta.get("name"))
    artist_url = artist_meta.get("external_urls", {}).get("spotify")
    
    results = sp.artist_albums(aid, album_type='album,single,compilation')
    albums = results['items']
    while results['next']:
        results = sp.next(results)
        albums.extend(results['items'])
        time.sleep(0.2)

    overview_lines = []
    details_orig = []
    links_orig = []
    links_new = []
    links_old = []

    print(f"[PROCESS] Found {len(albums)} albums. Processing...")

    for i, al in enumerate(albums, 1):
        try:
            al_name = clean_name(al["name"])
            if not al_name:
                al_name = f"Album {i}"

            al_url = al["external_urls"]["spotify"]
            al_date = al.get("release_date", "0000")
            al_total = al.get("total_tracks", 0)
            
            block = f"\nAlbum      : {al_name}\nLink       : {al_url}\nReleased   : {al_date}\nTracks     : {al_total}\n"
            overview_lines.append(block)

            tracks = fetch_album_tracks(sp, al["id"], al_date, al_name)
            
            tracks_new = sorted(tracks, key=lambda x: x["date"], reverse=True)
            tracks_old = sorted(tracks, key=lambda x: x["date"], reverse=False)

            sec_header = f"{al_name} ({al_date})"
            
            details_header = build_section_header(sec_header)
            detail_lines = []
            for idx, t in enumerate(tracks, 1):
                safe_track_name = clean_name(t['name'])
                safe_artist_name = clean_name(t['artist'])
                safe_album_name = clean_name(t['album'])
                detail_lines.append(f"{idx:02}. {safe_artist_name} – {safe_track_name} ({safe_album_name}) [{t['duration']}]")
            details_orig.append(details_header + "\n".join(detail_lines))

            link_header = build_section_header(sec_header)
            links_orig.append(link_header + "\n".join([t['link'] for t in tracks]))

            link_header_new = build_section_header(f"{sec_header} [Sorted New]")
            links_new.append(link_header_new + "\n".join([t['link'] for t in tracks_new]))

            link_header_old = build_section_header(f"{sec_header} [Sorted Old]")
            links_old.append(link_header_old + "\n".join([t['link'] for t in tracks_old]))
            
            print(f"  [OK] Processed {i}/{len(albums)}: {al_name}")
        except Exception as e:
            print(f"  [ERROR] Failed to process album {i} ({al_name}): {e}")
            continue

    header_block = build_header(f"{artist_name} Export", artist_url)
    
    print(f"[WRITE] Creating export files for: {artist_name}")
    
    # CHANGED: Added config checks for artist exports
    if config.get("overview_file"):
        write_content(session_dir / f"{artist_name} - Overview.txt", header_block + "\n".join(overview_lines))
    if config.get("details_full_file"):
        write_content(session_dir / f"{artist_name} - Full Details.txt", header_block + "\n".join(details_orig))
    if config.get("details_with_links_file"):
        write_content(session_dir / f"{artist_name} - Full Details with Links.txt", header_block + "\n".join(links_orig))
    if config.get("links_newest_file"):
        write_content(session_dir / f"{artist_name} - Links Newest to Oldest.txt", header_block + "\n".join(links_new))
    if config.get("links_oldest_file"):
        write_content(session_dir / f"{artist_name} - Links Oldest to Newest.txt", header_block + "\n".join(links_old))

def create_help_file():
    content = """Overview
This script exports Spotify data into plain .txt files.
It supports playlist, user, and artist links.
All output files are saved in the exports folder.

Supported links

* Playlist
* User profile
* Artist

What gets exported

Playlist link

* Playlist information
* Track links (original order)
* Track links sorted newest to oldest
* Track links sorted oldest to newest

User link

* Playlist overview
* Full track list (artist – track name)
* Full track list with Spotify links
* Track links (original order)
* Track links sorted newest to oldest
* Track links sorted oldest to newest

Artist link

* Album overview
* Full track list per album
* Full track list with Spotify links
* Track links sorted newest to oldest
* Track links sorted oldest to newest

Requirements

* Python 3
* Internet connection
* Spotify developer account

Setup

1. Put the script file in any folder
2. Open the folder in a terminal
3. Run the script once
4. If needed, spotipy will be installed automatically
5. Open spotify_keys.txt
6. Fill in your credentials

CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret

Get keys from
https://developer.spotify.com/dashboard

Authorization (first run only)

* A browser will open
* Log in to Spotify
* Approve access
* Copy the full redirect URL
* Paste it into the terminal and press Enter
* A .cache file will be created

Usage

1. Run the script
2. Paste a Spotify playlist, user, or artist URL
3. Press Enter
4. Wait until export is finished
5. Open the exports folder

Cache

* .cache stores your Spotify token
* Prevents re-authorization on future runs
* Delete it only if you want to re-login

Notes

* Only playlists visible to the authorized account can be exported
* Private playlists require your own credentials
* All files are plain text, no formatting, ready for direct use
* Edit config.txt to toggle specific export files on or off"""
    help_path = BASE_DIR / "help.txt"
    help_path.write_text(content, encoding="utf-8")

def main():
    try:
        print("\n" + "=" * 80)
        print("  SPOTIFY EXPORT TOOL".center(80))
        print("=" * 80 + "\n")

        EXPORT_DIR.mkdir(exist_ok=True)
        create_help_file()
        
        # CHANGED: Load configuration
        config = load_config()

        cid, sec = load_credentials()
        
        print("[INFO] Connecting to Spotify...")
        try:
            sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=cid,
                client_secret=sec,
                redirect_uri="https://oauth.pstmn.io/v1/callback",
                scope="playlist-read-private playlist-read-collaborative",
                cache_path=str(CACHE_FILE)
            ))
            print("[OK] Connected.\n")
        except Exception as e:
            print(f"[ERROR] Spotify connection failed: {e}")
            input("Press Enter to close...")
            return

        print("[INPUT] Please paste a Spotify Playlist, User or Artist URL:")
        url = input(">>> ").strip()
        
        if "/playlist/" in url:
            pid = url.split("/playlist/")[-1].split("?")[0]
            # CHANGED: Pass config to export function
            export_playlist(sp, pid, EXPORT_DIR, config)
        elif "/user/" in url:
            uid = url.split("/user/")[-1].split("?")[0]
            export_user(sp, uid, EXPORT_DIR, config)
        elif "/artist/" in url:
            aid = url.split("/artist/")[-1].split("?")[0]
            export_artist(sp, aid, EXPORT_DIR, config)
        else:
            print("\n[ERROR] Invalid URL. Please provide a valid Playlist, User or Artist link.")

        print("\n[DONE] Export process finished.")
        
    except Exception:
        print("\n" + "=" * 80)
        print("[FATAL ERROR] The script crashed unexpectedly.")
        print("=" * 80)
        traceback.print_exc()
        print("=" * 80)
    finally:
        input("\nPress Enter to close...")

if __name__ == "__main__":
    main()
