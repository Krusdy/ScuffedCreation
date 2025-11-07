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
open(os.path.join(base,"how_to_use.txt"),"w",encoding="utf-8").write("""SpotifyPlaylistFetcher — Usage Guide

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
- Private or hidden playlists are not included
""")
keyfile=os.path.join(base,"spotify_keys.txt")
if not os.path.exists(keyfile):
    open(keyfile,"w",encoding="utf-8").write("CLIENT_ID=\nCLIENT_SECRET=")
    print("spotify_keys.txt created. Fill in your keys.")
    sys.exit()
raw=open(keyfile,"r",encoding="utf-8").read().splitlines()
CID=""
SEC=""
for line in raw:
    if line.startswith("CLIENT_ID="):CID=line.replace("CLIENT_ID=","").strip()
    if line.startswith("CLIENT_SECRET="):SEC=line.replace("CLIENT_SECRET=","").strip()
if not CID or not SEC:
    print("Invalid keys in spotify_keys.txt")
    sys.exit()
os.makedirs(os.path.join(base,"exports"),exist_ok=True)
def clean_name(x):return re.sub(r'[\\/*?:"<>|]',"",x).strip()
def is_gibberish(s):return not s or len(s.strip())<2
def now():
    t=datetime.now().astimezone()
    o=t.strftime("%z")
    return t.strftime("%d %B %Y %H:%M:%S")+" UTC"+o[:3]
def write_header(f,title,link,desc=None):
    f.write("========================================\n")
    f.write("Title: "+title+"\n")
    f.write("URL: "+link+"\n")
    if desc is not None:f.write("Description: "+desc+"\n")
    f.write("Generated: "+now()+"\n")
    f.write("========================================\n\n")
sp=spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CID,client_secret=SEC,redirect_uri="https://oauth.pstmn.io/v1/callback",scope="playlist-read-private playlist-read-collaborative user-library-read",cache_path=os.path.join(base,".cache")))
url=input("Spotify link: ").strip()
eid=url.split("/")[-1].split("?")[0]
if "/playlist/" in url:
    d=sp.playlist(eid)
    en=clean_name(d["name"])
    out=os.path.join(base,"exports",en+".txt")
    link_out=os.path.join(base,"exports",en+" - Links.txt")
    with open(out,"w",encoding="utf-8")as f, open(link_out,"w",encoding="utf-8")as lf:
        ds=d.get("description")or"(No Description)"
        write_header(f,d["name"],d["external_urls"]["spotify"],ds)
        write_header(lf,d["name"],d["external_urls"]["spotify"],ds)
        t=d["tracks"]
        i=t.get("items",[])
        if not i:
            f.write("(No Tracks)\n")
            lf.write("(No Tracks)\n")
        else:
            c=1
            while t:
                for item in t["items"]:
                    o=item["track"]
                    if o:
                        n=o.get("name","(No Name)")
                        a=", ".join(x["name"]for x in o.get("artists",[]))
                        url=o.get("external_urls",{}).get("spotify","(No Link)")
                        f.write(str(c)+". "+n+" — "+a+"\n")
                        lf.write(url+"\n")
                        c+=1
                t=sp.next(t) if t["next"] else None
        f.write("\n")
        lf.write("\n")
    print("Saved: "+out)
    print("Saved links only: "+link_out)
elif "/artist/" in url:
    a=sp.artist(eid)
    albums=sp.artist_albums(eid,album_type="album,single",limit=50)
    en=clean_name(a["name"])
    b=os.path.join(base,"exports",en+" - Albums Overview.txt")
    f2=os.path.join(base,"exports",en+" - Albums Full Details.txt")
    link_full=os.path.join(base,"exports",en+" - Albums Full Details Links.txt")
    all_links_file=os.path.join(base,"exports",en+" - All Tracks Links.txt")
    with open(b,"w",encoding="utf-8")as fb:
        write_header(fb,en+" — Albums Overview",a.get("external_urls",{}).get("spotify",""))
        for album in albums["items"]:
            n=album.get("name","(No Name)")
            fb.write("- "+n+"\n\n")
    print("Saved: "+b)
    with open(f2,"w",encoding="utf-8")as ff, open(link_full,"w",encoding="utf-8")as lf, open(all_links_file,"w",encoding="utf-8")as af:
        write_header(ff,en+" — Albums Full Details",a.get("external_urls",{}).get("spotify",""))
        write_header(lf,en+" — Albums Full Details Links",a.get("external_urls",{}).get("spotify",""))
        af.write("========================================\n")
        af.write(f"Title: {en} — All Tracks Links\n")
        af.write(f"URL: {a.get('external_urls',{}).get('spotify','')}\n")
        af.write("Generated: "+now()+"\n")
        af.write("========================================\n\n")
        for album in albums["items"]:
            n=album.get("name","(No Name)")
            pid=album.get("id")
            ff.write("----------------------------------------\n")
            ff.write("Album: "+n+"\n\n")
            lf.write("----------------------------------------\n")
            lf.write("Album: "+n+"\n\n")
            tracks=sp.album_tracks(pid)
            if not tracks.get("items"):
                ff.write("(No Tracks)\n\n")
                lf.write("(No Tracks)\n\n")
                continue
            c=1
            while tracks:
                for item in tracks["items"]:
                    nm=item.get("name","(No Name)")
                    url=item.get("external_urls",{}).get("spotify","(No Link)")
                    ff.write(str(c)+". "+nm+"\n")
                    lf.write(url+"\n")
                    af.write(url+"\n")
                    c+=1
                tracks=sp.next(tracks) if tracks.get("next") else None
            ff.write("\n")
            lf.write("\n")
    print("Saved: "+f2)
    print("Saved links only: "+link_full)
    print("Saved all tracks links: "+all_links_file)
elif "/user/" in url:
    u=sp.user(eid)
    dn=u.get("display_name")or""
    un=u.get("id")
    fn=un if is_gibberish(dn)else dn
    fn=clean_name(fn)
    pls=sp.user_playlists(eid)
    b=os.path.join(base,"exports",fn+" - Playlists Overview.txt")
    f2=os.path.join(base,"exports",fn+" - Playlists Full Details.txt")
    link_full=os.path.join(base,"exports",fn+" - Playlists Full Details Links.txt")
    all_links_file=os.path.join(base,"exports",fn+" - All Tracks Links.txt")
    with open(b,"w",encoding="utf-8")as fb:
        write_header(fb,fn+" — Playlists Overview",u.get("external_urls",{}).get("spotify",""))
        for pl in pls["items"]:
            n=pl.get("name","(No Name)")
            d=pl.get("description") or "(No Description)"
            fb.write("- "+n+"\n")
            fb.write("  "+d+"\n\n")
    print("Saved: "+b)
    with open(f2,"w",encoding="utf-8")as ff, open(link_full,"w",encoding="utf-8")as lf, open(all_links_file,"w",encoding="utf-8")as af:
        write_header(ff,fn+" — Playlists Full Details",u.get("external_urls",{}).get("spotify",""))
        write_header(lf,fn+" — Playlists Full Details Links",u.get("external_urls",{}).get("spotify",""))
        af.write("========================================\n")
        af.write(f"Title: {fn} — All Tracks Links\n")
        af.write(f"URL: {u.get('external_urls',{}).get('spotify','')}\n")
        af.write("Generated: "+now()+"\n")
        af.write("========================================\n\n")
        for pl in pls["items"]:
            n=pl.get("name","(No Name)")
            pid=pl.get("id")
            ff.write("----------------------------------------\n")
            ff.write("Playlist: "+n+"\n")
            ff.write("Description: "+(pl.get("description")or"(No Description)")+"\n\n")
            lf.write("----------------------------------------\n")
            lf.write("Playlist: "+n+"\n")
            lf.write("Description: "+(pl.get("description")or"(No Description)")+"\n\n")
            t=sp.playlist_tracks(pid)
            if not t.get("items"):
                ff.write("(No Tracks)\n\n")
                lf.write("(No Tracks)\n\n")
                af.write("(No Tracks)\n")
                continue
            c=1
            while t:
                for item in t["items"]:
                    o=item.get("track")
                    if o:
                        nm=o.get("name","(No Name)")
                        a=", ".join(x["name"]for x in o.get("artists",[]))
                        url=o.get("external_urls",{}).get("spotify","(No Link)")
                        ff.write(str(c)+". "+nm+" — "+a+"\n")
                        lf.write(url+"\n")
                        af.write(url+"\n")
                        c+=1
                t=sp.next(t) if t.get("next") else None
            ff.write("\n")
            lf.write("\n")
    print("Saved: "+f2)
    print("Saved links only: "+link_full)
    print("Saved all tracks links: "+all_links_file)
else:
    print("Unsupported link.")
