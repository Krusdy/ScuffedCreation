import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re

CLIENT_ID = "3f3f1310a4134bdfbd1dc75741deaa34"
CLIENT_SECRET = "0779aa691cea4f47a2b9c4f893e3400f"
REDIRECT_URI = "https://oauth.pstmn.io/v1/callback"
SCOPE = "playlist-read-private playlist-read-collaborative user-library-read"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
))

PROFILE_URL = input("Paste Spotify link: ").strip()
entity_id = PROFILE_URL.split("/")[-1].split("?")[0]

if "/playlist/" in PROFILE_URL:
    playlist_info = sp.playlist(entity_id)
    entity_name = re.sub(r'[\\/*?:"<>|]', "", playlist_info['name'])
    OUTPUT_FILE = f"{entity_name}.txt"
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"{playlist_info['name']} - {playlist_info['external_urls']['spotify']}\n")
        f.write(f"Description: {playlist_info.get('description','(none)')}\n\n")
        tracks = playlist_info['tracks']
        while tracks:
            for item in tracks['items']:
                track = item['track']
                if track:
                    track_name = track['name']
                    artists = ", ".join([artist['name'] for artist in track['artists']])
                    f.write(f"{track_name} - {artists}\n")
            tracks = sp.next(tracks) if tracks['next'] else None
    print(f"Saved playlist to {OUTPUT_FILE}")

elif "/artist/" in PROFILE_URL:
    artist_info = sp.artist(entity_id)
    playlists = sp.artist_albums(entity_id, album_type='album,single', limit=50)
    entity_name = re.sub(r'[\\/*?:"<>|]', "", artist_info['name'])
    OUTPUT_FILE = f"{entity_name}_artist.txt"
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(f"Artist: {artist_info['name']} - {artist_info['external_urls']['spotify']}\n")
        f.write(f"Followers: {artist_info['followers']['total']}\n")
        f.write(f"Genres: {', '.join(artist_info['genres'])}\n\n")
        for album in playlists['items']:
            f.write(f"{album['name']} - {album['external_urls']['spotify']}\n")
    print(f"Saved artist info to {OUTPUT_FILE}")

elif "/user/" in PROFILE_URL:
    user_playlists = sp.user_playlists(entity_id)
    entity_name = re.sub(r'[\\/*?:"<>|]', "", entity_id)
    OUTPUT_FILE = f"{entity_name}_profile.txt"
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for playlist in user_playlists['items']:
            f.write(f"{playlist['name']} - {playlist['external_urls']['spotify']}\n")
            f.write(f"Description: {playlist.get('description','(none)')}\n\n")
    print(f"Saved profile playlists to {OUTPUT_FILE}")

else:
    print("Unsupported Spotify link.")
