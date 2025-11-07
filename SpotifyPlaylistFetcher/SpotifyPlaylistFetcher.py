import sys
sys.path.insert(0, "libs")

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re
import os
from datetime import datetime, timezone

CLIENT_ID = "3f3f1310a4134bdfbd1dc75741deaa34"
CLIENT_SECRET = "-"
REDIRECT_URI = "https://oauth.pstmn.io/v1/callback"
SCOPE = "playlist-read-private playlist-read-collaborative user-library-read"

os.makedirs("exports", exist_ok=True)

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
))

PROFILE_URL = input("Paste Spotify link: ").strip()
entity_id = PROFILE_URL.split("/")[-1].split("?")[0]

def clean_name(x):
    return re.sub(r'[\\/*?:"<>|]', "", x).strip()

def is_gibberish(s):
    return not s or len(s.strip()) < 2

def now():
    t = datetime.now().astimezone()
    offset = t.strftime("%z")
    return t.strftime("%d %B %Y %H:%M:%S") + f" UTC{offset[:3]}"

def write_header(f, title, link, desc):
    f.write("========================================\n")
    f.write(f"Title: {title}\n")
    f.write(f"URL: {link}\n")
    f.write(f"Description: {desc if desc else '(No Description)'}\n")
    f.write(f"Generated: {now()}\n")
    f.write("========================================\n\n")

if "/playlist/" in PROFILE_URL:
    playlist_info = sp.playlist(entity_id)
    entity_name = clean_name(playlist_info['name'])
    OUTPUT_FILE = f"exports/{entity_name}.txt"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        desc = playlist_info.get('description') or "(No Description)"
        write_header(
            f,
            playlist_info['name'],
            playlist_info['external_urls']['spotify'],
            desc
        )

        tracks = playlist_info['tracks']
        items = tracks.get("items", [])

        if not items:
            f.write("(No Tracks)\n")
        else:
            index = 1
            while tracks:
                for item in tracks['items']:
                    track = item['track']
                    if track:
                        name = track['name']
                        artists = ", ".join(a['name'] for a in track['artists'])
                        f.write(f"{index}. {name} — {artists}\n")
                        index += 1
                tracks = sp.next(tracks) if tracks['next'] else None

    print(f"Saved → {OUTPUT_FILE}")

elif "/artist/" in PROFILE_URL:
    artist_info = sp.artist(entity_id)
    albums = sp.artist_albums(entity_id, album_type='album,single', limit=50)
    entity_name = clean_name(artist_info['name'])
    OUTPUT_FILE = f"exports/{entity_name} - Artist Overview.txt"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        write_header(
            f,
            artist_info['name'],
            artist_info['external_urls']['spotify'],
            None
        )
        f.write(f"Followers: {artist_info['followers']['total']}\n")
        f.write(f"Genres: {', '.join(artist_info['genres'])}\n\n")

        for album in albums['items']:
            f.write(f"- {album['name']} — {album['external_urls']['spotify']}\n")

    print(f"Saved → {OUTPUT_FILE}")

elif "/user/" in PROFILE_URL:
    user = sp.user(entity_id)
    display_name = user.get("display_name") or ""
    username = user.get("id")

    final_name = username if is_gibberish(display_name) else display_name
    final_name = clean_name(final_name)

    user_playlists = sp.user_playlists(entity_id)

    basic_file = f"exports/{final_name} - Playlists Overview.txt"
    full_file = f"exports/{final_name} - Playlists Full Details.txt"

    with open(basic_file, "w", encoding="utf-8") as fb:
        write_header(
            fb,
            f"{final_name} — Playlists Overview",
            user.get("external_urls", {}).get("spotify", ""),
            None
        )
        for playlist in user_playlists['items']:
            n = playlist['name']
            d = playlist.get('description') or "(No Description)"
            fb.write(f"- {n}\n")
            fb.write(f"  {d}\n\n")

    print(f"Saved → {basic_file}")

    with open(full_file, "w", encoding="utf-8") as ff:
        write_header(
            ff,
            f"{final_name} — Playlists Full Details",
            user.get("external_urls", {}).get("spotify", ""),
            None
        )

        for playlist in user_playlists['items']:
            n = playlist['name']
            d = playlist.get('description') or "(No Description)"
            ff.write("----------------------------------------\n")
            ff.write(f"Playlist: {n}\n")
            ff.write(f"Description: {d}\n\n")

            playlist_id = playlist['id']
            tracks = sp.playlist_tracks(playlist_id)
            items = tracks.get("items", [])

            if not items:
                ff.write("(No Tracks)\n\n")
                continue

            index = 1
            while tracks:
                for item in tracks['items']:
                    track = item['track']
                    if track:
                        name = track['name']
                        artists = ", ".join(a['name'] for a in track['artists'])
                        ff.write(f"{index}. {name} — {artists}\n")
                        index += 1
                tracks = sp.next(tracks) if tracks['next'] else None

            ff.write("\n")

    print(f"Saved → {full_file}")

else:
    print("Unsupported Spotify link.")
