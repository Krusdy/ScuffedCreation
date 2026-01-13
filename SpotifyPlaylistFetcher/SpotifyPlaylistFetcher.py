import os,sys,re,subprocess
from datetime import datetime

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
except:
    subprocess.run([sys.executable,"-m","pip","install","spotipy"],stdout=subprocess.DEVNULL)
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth

base=os.path.dirname(os.path.abspath(__file__))
open(os.path.join(base,"how_to_use.txt"),"w",encoding="utf-8").write("SpotifyPlaylistFetcher — Usage Guide

Overview
This tool exports Spotify data into .txt files for easy reference.

Features
- User link: Overview, Full Details, Full Details Links, All Tracks Links
- Playlist link: Playlist Info, Playlist Links
- Artist link: Albums Overview, Full Details, Full Details Links, All Tracks Links

Setup
1) Place SpotifyPlaylistFetcher.py in a folder
2) Open VS Code
3) Open terminal (Ctrl + `)
4) Run:
   python -m pip install spotipy
5) Open spotify_keys.txt
6) Replace CLIENT_ID and CLIENT_SECRET with your own values from https://developer.spotify.com/dashboard

Usage
1) Run:
   python SpotifyPlaylistFetcher.py
2) Paste a Spotify user, playlist, or artist link
3) Approve authorization if prompted
4) Copy redirected URL and paste into terminal
5) All exports are stored in the 'exports' folder

Cache
A .cache file stores your Spotify token after first authorization

Notes
- Only PUBLIC playlists are accessible
- Private or hidden playlists are not included")

keyfile=os.path.join(base,"spotify_keys.txt")
if not os.path.exists(keyfile):
    open(keyfile,"w",encoding="utf-8").write("CLIENT_ID=\nCLIENT_SECRET=")
    sys.exit()

raw=open(keyfile,"r",encoding="utf-8").read().splitlines()
CID=SEC=""
for line in raw:
    if line.startswith("CLIENT_ID="):CID=line.replace("CLIENT_ID=","").strip()
    if line.startswith("CLIENT_SECRET="):SEC=line.replace("CLIENT_SECRET=","").strip()
if not CID or not SEC:sys.exit()

os.makedirs(os.path.join(base,"exports"),exist_ok=True)

def clean_name(x):return re.sub(r'[\\/*?:"<>|]',"",x).strip()
def now():
    t=datetime.now().astimezone()
    o=t.strftime("%z")
    return t.strftime("%d %B %Y %H:%M:%S")+" UTC"+o[:3]

sp=spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CID,
    client_secret=SEC,
    redirect_uri="https://oauth.pstmn.io/v1/callback",
    scope="playlist-read-private playlist-read-collaborative",
    cache_path=os.path.join(base,".cache")
))

url=input("Spotify playlist link: ").strip()
if "/playlist/" not in url:sys.exit()

eid=url.split("/")[-1].split("?")[0]
d=sp.playlist(eid)
en=clean_name(d["name"])

out_new=os.path.join(base,"exports",en+" - Links Newest to Oldest.txt")
out_old=os.path.join(base,"exports",en+" - Links Oldest to Newest.txt")

tracks=[]
t=d["tracks"]
while t:
    for item in t.get("items",[]):
        o=item.get("track")
        if not o:continue
        link=o.get("external_urls",{}).get("spotify","")
        album=o.get("album",{})
        rel=album.get("release_date","0000-00-00")
        tracks.append({"release":rel,"link":link})
    t=sp.next(t) if t.get("next") else None

tracks_new=sorted(tracks,key=lambda x:x["release"],reverse=True)
tracks_old=sorted(tracks,key=lambda x:x["release"])

with open(out_new,"w",encoding="utf-8")as f:
    f.write("========================================\n")
    f.write("Title: "+d["name"]+"\n")
    f.write("URL: "+d["external_urls"]["spotify"]+"\n")
    f.write("Sorted: Newest → Oldest\n")
    f.write("Generated: "+now()+"\n")
    f.write("========================================\n\n")
    for x in tracks_new:f.write(x["link"]+"\n")

with open(out_old,"w",encoding="utf-8")as f:
    f.write("========================================\n")
    f.write("Title: "+d["name"]+"\n")
    f.write("URL: "+d["external_urls"]["spotify"]+"\n")
    f.write("Sorted: Oldest → Newest\n")
    f.write("Generated: "+now()+"\n")
    f.write("========================================\n\n")
    for x in tracks_old:f.write(x["link"]+"\n")

print("Saved:")
print(out_new)
print(out_old)
