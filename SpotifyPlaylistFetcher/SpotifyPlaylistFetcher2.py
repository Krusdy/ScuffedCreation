import sys
import re
import subprocess
import time
import webbrowser
import os
from datetime import datetime
from pathlib import Path
import traceback

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    from spotipy.exceptions import SpotifyException
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "spotipy"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    from spotipy.exceptions import SpotifyException

BASE_DIR = Path(__file__).parent.resolve()
EXPORT_DIR = BASE_DIR / "exports"
KEY_FILE = BASE_DIR / "spotify_keys.txt"
CACHE_FILE = BASE_DIR / ".cache"

EXPORT_DIR.mkdir(exist_ok=True)

def load_credentials():
    if not KEY_FILE.exists():
        print(" [!] Credentials file missing.")
        KEY_FILE.write_text("CLIENT_ID = \nCLIENT_SECRET = ", encoding="utf-8")
        sys.exit()

    creds = {}
    for line in KEY_FILE.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, val = line.split("=", 1)
            creds[key.strip()] = val.strip()
            
    if not creds.get("CLIENT_ID") or not creds.get("CLIENT_SECRET"):
        print(" [!] Client ID or Secret missing in file.")
        sys.exit()
    return creds["CLIENT_ID"], creds["CLIENT_SECRET"]

def get_safe_name(name):
    if not name:
        return ""
    name = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    name = name.encode("ascii", "ignore").decode("ascii")
    return name.strip()

def get_timestamp():
    t = datetime.now().astimezone()
    offset = t.strftime("%z")
    return f"{t.strftime('%Y-%m-%d %H:%M:%S')} UTC{offset[:3]}"

def format_duration(ms):
    seconds = ms // 1000
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"

def build_header(title, url, sort_type, content_type="Playlist"):
    line = "═" * 80
    spacer = "║" + " " * 78 + "║"
    header = f"{line}\n║  Spotify Export Report\n{line}\n"
    header += f"║  Title      : {title}\n{spacer}\n"
    header += f"║  Type       : {content_type.title()}\n║  Source Url : {url}\n"
    if sort_type:
        header += f"║  Sort Order : {sort_type.title()}\n"
    header += f"║  Generated  : {get_timestamp()}\n{line}\n\n"
    return header

def build_section_header(title):
    line = "─" * 80
    return f"\n{line}\n  {title.title()}\n{line}\n"

def fetch_playlist_tracks(sp, playlist_id):
    tracks = []
    try:
        # KHÔNG dùng market='from_token' để tránh lỗi nếu User chưa set quốc gia
        # Nếu vẫn lỗi, Spotify sẽ trả về track.is_playable = False, nhưng chúng ta vẫn lấy được tên
        results = sp.playlist_items(playlist_id, limit=100)
        
        api_total = results.get('total', 0)
        print(f" [~] Spotify API reports Total Tracks: {api_total}")
        if api_total == 0:
            print(" [!] API reported 0 tracks. This is likely a 403 Permission error or Empty Playlist.")

    except SpotifyException as e:
        # Nếu lỗi 403, RE-RAISE (ném lại lỗi) để hàm main xử lý và hiện thông báo Whitelist
        print(f" [!] Critical API Error in fetch_playlist_tracks: {e}")
        raise e
    except Exception as e:
        print(f" [!] Unexpected Error: {e}")
        return []

    while results:
        items = results.get("items", [])
        
        for item in items:
            track = item.get("track")
            episode = item.get("episode")
            
            # Xử lý Track thông thường
            if track:
                # BỎ QUA check is_local hoặc ID rỗng để xem có dữ liệu trả về không
                # Chỉ skip nếu tên trống
                if not track.get("name"):
                    continue
                
                artists = ", ".join([a["name"] for a in track.get("artists", [])])
                tracks.append({
                    "name": track["name"],
                    "artist": artists,
                    "link": track["external_urls"].get("spotify", "#"),
                    "date": track.get("album", {}).get("release_date", "0000"),
                    "duration": format_duration(track.get("duration_ms", 0))
                })
            elif episode:
                # Ghi nhận có episode nhưng không xuất
                pass
        
        if results.get("next"):
            results = sp.next(results)
        else:
            results = None
        time.sleep(0.1)
        
    print(f" [+] Collected {len(tracks)} track objects (after parsing).")
    return tracks

def fetch_album_tracks(sp, album_id, album_date):
    tracks = []
    results = sp.album_tracks(album_id)
    while results:
        for item in results.get("items", []):
            artists = ", ".join([a["name"] for a in item.get("artists", [])])
            tracks.append({
                "name": item["name"],
                "artist": artists,
                "link": item["external_urls"]["spotify"],
                "date": album_date,
                "duration": format_duration(item.get("duration_ms", 0))
            })
        if results.get("next"):
            results = sp.next(results)
        else:
            results = None
        time.sleep(0.2)
    return tracks

def write_content(filepath, content):
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

def export_single_list(sp, tracks, raw_name, url, session_dir, content_type):
    print(f" [~] Processing tracks for sorting...")
    
    tracks_new = sorted(tracks, key=lambda x: x["date"], reverse=True)
    tracks_old = sorted(tracks, key=lambda x: x["date"], reverse=False)
    tracks_orig = tracks

    safe_name = get_safe_name(raw_name)

    def get_name_string(t):
        return f"{t['artist']} – {t['name']}"

    print(f" [~] Writing export files to disk...")

    write_content(session_dir / f"{safe_name} - Links Newest to Oldest.txt", 
                  build_header(raw_name, url, "Newest To Oldest", content_type) + "\n".join([t['link'] for t in tracks_new]))
    
    write_content(session_dir / f"{safe_name} - Links Oldest to Newest.txt", 
                  build_header(raw_name, url, "Oldest To Newest", content_type) + "\n".join([t['link'] for t in tracks_old]))
    
    write_content(session_dir / f"{safe_name} - Links Original Order.txt", 
                  build_header(raw_name, url, "Original Order", content_type) + "\n".join([t['link'] for t in tracks_orig]))

    write_content(session_dir / f"{safe_name} - Songs Name Newest to Oldest.txt", 
                  build_header(raw_name, url, "Newest To Oldest", content_type) + "\n".join([get_name_string(t) for t in tracks_new]))
    
    write_content(session_dir / f"{safe_name} - Songs Name Oldest to Newest.txt", 
                  build_header(raw_name, url, "Oldest To Newest", content_type) + "\n".join([get_name_string(t) for t in tracks_old]))
    
    write_content(session_dir / f"{safe_name} - Songs Name Original Order.txt", 
                  build_header(raw_name, url, "Original Order", content_type) + "\n".join([get_name_string(t) for t in tracks_orig]))

def export_user(sp, uid, session_dir):
    print(f" [~] Fetching user profile data...")
    try:
        user_meta = sp.user(uid)
    except Exception as e:
        print(f" [!] Could not fetch user profile: {e}")
        return

    raw_user_name = user_meta.get("display_name") or uid
    safe_user_name = get_safe_name(raw_user_name)
    
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

    print(f" [~] Found {len(playlists)} playlists. Processing content...")

    for i, pl in enumerate(playlists, 1):
        try:
            raw_pl_name = pl["name"]
            safe_pl_name = get_safe_name(raw_pl_name)
            if not safe_pl_name:
                safe_pl_name = f"Playlist {i}"
                
            pl_url = pl["external_urls"]["spotify"]
            pl_desc = pl.get("description") or "No description"
            pl_count = pl.get("tracks", {}).get("total", 0)
            
            block = f"\n  Name        : {raw_pl_name}\n  Link        : {pl_url}\n  Tracks      : {pl_count}\n  Description : {pl_desc}\n"
            overview_lines.append(block)

            tracks = fetch_playlist_tracks(sp, pl["id"])
            
            tracks_new = sorted(tracks, key=lambda x: x["date"], reverse=True)
            tracks_old = sorted(tracks, key=lambda x: x["date"], reverse=False)

            sec_header = build_section_header(f"{raw_pl_name} ({pl_count} Tracks)")
            
            detail_lines = []
            for idx, t in enumerate(tracks, 1):
                detail_lines.append(f"  {idx:02}. {t['artist']} – {t['name']} ({t.get('album', 'N/A')}) [{t['duration']}]")
            details_orig.append(sec_header + "\n".join(detail_lines))

            links_orig.append(sec_header + "\n".join([t['link'] for t in tracks]))
            links_new.append(build_section_header(f"{raw_pl_name} [Sorted New]") + "\n".join([t['link'] for t in tracks_new]))
            links_old.append(build_section_header(f"{raw_pl_name} [Sorted Old]") + "\n".join([t['link'] for t in tracks_old]))
            
            print(f"     - Analyzed playlist {i}/{len(playlists)}")
        except Exception as e:
            print(f"     - Error processing playlist {i}: {e}")
            continue

    header_block = build_header(f"{raw_user_name} Profile", f"https://open.spotify.com/user/{uid}", None, "User Profile")
    
    print(f" [~] Writing profile exports...")
    write_content(session_dir / f"{safe_user_name} - Overview.txt", header_block + "\n" + "\n".join(overview_lines))
    write_content(session_dir / f"{safe_user_name} - Full Details.txt", header_block + "\n" + "\n".join(details_orig))
    write_content(session_dir / f"{safe_user_name} - Full Details with Links.txt", header_block + "\n" + "\n".join(links_orig))
    write_content(session_dir / f"{safe_user_name} - Links Newest to Oldest.txt", header_block + "\n" + "\n".join(links_new))
    write_content(session_dir / f"{safe_user_name} - Links Oldest to Newest.txt", header_block + "\n" + "\n".join(links_old))

def export_artist(sp, aid, session_dir):
    print(f" [~] Fetching artist data...")
    try:
        artist_meta = sp.artist(aid)
    except Exception as e:
        print(f" [!] Could not fetch artist profile: {e}")
        return
        
    raw_artist_name = artist_meta.get("name")
    safe_artist_name = get_safe_name(raw_artist_name)
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

    print(f" [~] Found {len(albums)} albums. Processing content...")

    for i, al in enumerate(albums, 1):
        try:
            raw_al_name = al["name"]
            safe_al_name = get_safe_name(raw_al_name)
            if not safe_al_name:
                safe_al_name = f"Album {i}"

            al_url = al["external_urls"]["spotify"]
            al_date = al.get("release_date", "0000")
            al_total = al.get("total_tracks", 0)
            
            block = f"\n  Name      : {raw_al_name}\n  Link      : {al_url}\n  Released  : {al_date}\n  Tracks    : {al_total}\n"
            overview_lines.append(block)

            tracks = fetch_album_tracks(sp, al["id"], al_date)
            
            tracks_new = sorted(tracks, key=lambda x: x["date"], reverse=True)
            tracks_old = sorted(tracks, key=lambda x: x["date"], reverse=False)

            sec_header = build_section_header(f"{raw_al_name} ({al_date})")
            
            detail_lines = []
            for idx, t in enumerate(tracks, 1):
                detail_lines.append(f"  {idx:02}. {t['artist']} – {t['name']} ({raw_al_name}) [{t['duration']}]")
            details_orig.append(sec_header + "\n".join(detail_lines))

            links_orig.append(sec_header + "\n".join([t['link'] for t in tracks]))
            links_new.append(build_section_header(f"{raw_al_name} [Sorted New]") + "\n".join([t['link'] for t in tracks_new]))
            links_old.append(build_section_header(f"{raw_al_name} [Sorted Old]") + "\n".join([t['link'] for t in tracks_old]))
            
            print(f"     - Analyzed album {i}/{len(albums)}")
        except Exception as e:
            print(f"     - Error processing album {i}: {e}")
            continue

    header_block = build_header(f"{raw_artist_name} Profile", artist_url, None, "Artist Profile")
    
    print(f" [~] Writing profile exports...")
    write_content(session_dir / f"{safe_artist_name} - Overview.txt", header_block + "\n" + "\n".join(overview_lines))
    write_content(session_dir / f"{safe_artist_name} - Full Details.txt", header_block + "\n" + "\n".join(details_orig))
    write_content(session_dir / f"{safe_artist_name} - Full Details with Links.txt", header_block + "\n" + "\n".join(links_orig))
    write_content(session_dir / f"{safe_artist_name} - Links Newest to Oldest.txt", header_block + "\n" + "\n".join(links_new))
    write_content(session_dir / f"{safe_artist_name} - Links Oldest to Newest.txt", header_block + "\n" + "\n".join(links_old))

def main():
    user = None
    try:
        print("\n" + "=" * 80)
        print("  Spotify Export Tool V3.9 (Final)".center(80))
        print("=" * 80)
        print("\n [!] CRITICAL SETUP CHECK:")
        print(" [1] Spotify Dashboard -> Redirect URIs MUST contain:")
        print("     >>> https://oauth.pstmn.io/v1/callback <<<")
        print(" [2] Your Email MUST be in 'User Management' Whitelist.")
        input("\n [?] Press Enter to confirm you checked this...")

        EXPORT_DIR.mkdir(exist_ok=True)
        cid, sec = load_credentials()
        
        if CACHE_FILE.exists():
            print(" [!] Clearing old cache to enforce fresh login...")
            os.remove(CACHE_FILE)
        
        scope = "playlist-read-private playlist-read-collaborative user-library-read user-read-email"
        redirect_uri = "https://oauth.pstmn.io/v1/callback"
        
        print("\n [!] AUTHENTICATION REQUIRED")
        auth_manager = SpotifyOAuth(
            client_id=cid,
            client_secret=sec,
            redirect_uri=redirect_uri,
            scope=scope,
            cache_path=str(CACHE_FILE),
            show_dialog=True,
            open_browser=False
        )
        auth_url = auth_manager.get_authorize_url()
        print(f" [URL] {auth_url}")
        
        choice = input("\n [?] Press 'O' to Open browser: ").strip().upper()
        if choice == 'O':
            webbrowser.open(auth_url)
        
        print("\n [?] Paste the Redirect URL (starts with https://oauth.pstmn.io...):")
        response_url = input(" >>> ").strip()
        code = auth_manager.parse_response_code(response_url)
        token_info = auth_manager.get_access_token(code)
        
        sp = spotipy.Spotify(auth_manager=auth_manager)
        user = sp.current_user()
        
        print("\n" + "=" * 80)
        print("  LOGIN SUCCESSFUL".center(80))
        print("=" * 80)
        print(f"  Name   : {user.get('display_name')}")
        print(f"  Email  : {user.get('email')}")
        print(f"  Country: {user.get('country')}")
        print("=" * 80)
        print(f"\n [!] IMPORTANT: Whitelist this email in Dashboard: {user.get('email')}\n")

        print(" [?] Paste a Spotify URL:")
        url = input(" >>> ").strip()
        
        if "/playlist/" in url:
            pid = url.split("/playlist/")[-1].split("?")[0]
            metadata = sp.playlist(pid)
            raw_name = metadata["name"]
            pl_url = metadata["external_urls"]["spotify"]
            
            print(f"\n [~] Fetching playlist: {raw_name}")
            tracks = fetch_playlist_tracks(sp, pid)
            
            if not tracks:
                print("\n [!] FATAL: No tracks were found.")
                print(" [!] This usually means:")
                print("     1. Your email is NOT whitelisted (Most Likely).")
                print("     2. The playlist contains ONLY local files (mp3s on your PC).")
            else:
                export_single_list(sp, tracks, raw_name, pl_url, EXPORT_DIR, "Playlist")
                print(f" [+] Successfully exported playlist: {raw_name}")

        elif "/album/" in url:
            aid = url.split("/album/")[-1].split("?")[0]
            metadata = sp.album(aid)
            raw_name = metadata["name"]
            al_url = metadata["external_urls"]["spotify"]
            date = metadata.get("release_date", "0000")
            
            print("\n [~] Fetching album: {raw_name}")
            tracks = fetch_album_tracks(sp, aid, date)
            export_single_list(sp, tracks, raw_name, al_url, EXPORT_DIR, "Album")
            print(f" [+] Successfully exported album: {raw_name}")

        elif "/user/" in url:
            uid = url.split("/user/")[-1].split("?")[0]
            export_user(sp, uid, EXPORT_DIR)
            print(" [+] Successfully exported user profile data")

        elif "/artist/" in url:
            aid = url.split("/artist/")[-1].split("?")[0]
            export_artist(sp, aid, EXPORT_DIR)
            print(" [+] Successfully exported artist profile data")

        else:
            print("\n [!] Invalid URL.")
            
        print("\n [Done] Check 'exports' folder.")
        
    except SpotifyException as e:
        print("\n" + "!" * 80)
        print(" [CRITICAL ERROR]".center(80))
        print("!" * 80)
        print(f" Status: {e.http_status}")
        print(f" Msg: {e.msg}")
        
        if e.http_status == 403:
            print("\n [REASON] 403 FORBIDDEN.")
            print(" [SOLUTION] You do NOT have permission to access this data.")
            if user:
                print(f" [ACTION] Go to Dashboard and Whitelist: {user.get('email')}")
            else:
                print(" [ACTION] Whitelist your account email in Spotify Dashboard.")
        elif e.http_status == 401:
            print("\n [REASON] 401 UNAUTHORIZED.")
            print(" [SOLUTION] Token expired or invalid. Check Client ID/Secret.")
        elif "redirect" in str(e).lower():
            print("\n [REASON] REDIRECT URI MISMATCH.")
            print(" [SOLUTION] Check Dashboard settings. Ensure HTTPS URL is added.")
        print("!" * 80)
    except Exception:
        print("\n [Fatal Error] Script crashed.")
        traceback.print_exc()
    finally:
        input("\nPress Enter to close...")

if __name__ == "__main__":
    main()
