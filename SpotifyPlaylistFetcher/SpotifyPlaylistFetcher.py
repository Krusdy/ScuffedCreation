import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re,sys
CLIENT_ID="3f3f1310a4134bdfbd1dc75741deaa34"
CLIENT_SECRET="0779aa691cea4f47a2b9c4f893e3400f"
REDIRECT_URI="https://oauth.pstmn.io/v1/callback"
SCOPE="playlist-read-private playlist-read-collaborative user-library-read"
url=input("Paste Spotify link: ").strip()
if not url.startswith("https://"):
    print("Invalid Spotify URL.");sys.exit(1)
eid=url.split("/")[-1].split("?")[0]
sp=spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID,client_secret=CLIENT_SECRET,redirect_uri=REDIRECT_URI,scope=SCOPE))
if "/playlist/" in url:
    p=sp.playlist(eid);name=re.sub(r'[\\/*?:"<>|]',"",p["name"]);out=f"{name}.txt"
    with open(out,"w",encoding="utf-8") as f:
        f.write(f"{p['name']} - {p['external_urls']['spotify']}\nDescription: {p.get('description','(none)')}\n\n")
        tracks=p["tracks"]
        while tracks:
            for i in tracks["items"]:
                t=i["track"]
                if t:f.write(f"{t['name']} - {', '.join(a['name'] for a in t['artists'])}\n")
            tracks=sp.next(tracks) if tracks["next"] else None
    print(f"Saved playlist to {out}")
elif "/artist/" in url:
    a=sp.artist(eid);albums=sp.artist_albums(eid,album_type="album,single",limit=50);name=re.sub(r'[\\/*?:"<>|]',"",a["name"]);out=f"{name}_artist.txt"
    with open(out,"w",encoding="utf-8") as f:
        f.write(f"Artist: {a['name']} - {a['external_urls']['spotify']}\nFollowers: {a['followers']['total']}\nGenres: {', '.join(a['genres'])}\n\n")
        for al in albums["items"]:f.write(f"{al['name']} - {al['external_urls']['spotify']}\n")
    print(f"Saved artist info to {out}")
elif "/user/" in url:
    u=sp.user_playlists(eid);name=re.sub(r'[\\/*?:"<>|]',"",eid);out=f"{name}_profile.txt"
    with open(out,"w",encoding="utf-8") as f:
        for pl in u["items"]:
            f.write(f"{pl['name']} - {pl['external_urls']['spotify']}\nDescription: {pl.get('description','(none)')}\n\n")
    print(f"Saved profile playlists to {out}")
else:print("Unsupported Spotify link type.")
