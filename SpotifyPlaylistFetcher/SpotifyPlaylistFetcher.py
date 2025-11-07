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
open(os.path.join(base,"how_to_use.txt"),"w",encoding="utf-8").write("Go to https://developer.spotify.com/dashboard Create an app Copy Client ID and Client Secret Put them into spotify_keys.txt as: CLIENT_ID=xxxx CLIENT_SECRET=xxxx")
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
def write_header(f,title,link,desc):
    f.write("========================================\n")
    f.write("Title: "+title+"\n")
    f.write("URL: "+link+"\n")
    f.write("Description: "+(desc if desc else "(No Description)")+"\n")
    f.write("Generated: "+now()+"\n")
    f.write("========================================\n\n")
    f.write("\n")
sp=spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CID,client_secret=SEC,redirect_uri="https://oauth.pstmn.io/v1/callback",scope="playlist-read-private playlist-read-collaborative user-library-read",cache_path=os.path.join(base,".cache")))
url=input("Spotify link: ").strip()
eid=url.split("/")[-1].split("?")[0]
if "/playlist/"in url:
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
                        n=o["name"]
                        a=", ".join(x["name"]for x in o["artists"])
                        url=o["external_urls"]["spotify"]
                        f.write(str(c)+". "+n+" — "+a+"\n")
                        lf.write(url+"\n")
                        c+=1
                t=sp.next(t)if t["next"]else None
        f.write("\n")
        lf.write("\n")
    print("Saved: "+out)
    print("Saved links only: "+link_out)
elif"/artist/"in url:
    a=sp.artist(eid)
    al=sp.artist_albums(eid,album_type="album,single",limit=50)
    en=clean_name(a["name"])
    out=os.path.join(base,"exports",en+" - Artist Overview.txt")
    with open(out,"w",encoding="utf-8")as f:
        write_header(f,a["name"],a["external_urls"]["spotify"],None)
        f.write("Followers: "+str(a["followers"]["total"])+"\n")
        f.write("Genres: "+", ".join(a["genres"])+"\n\n")
        for x in al["items"]:
            f.write("- "+x["name"]+" — "+x["external_urls"]["spotify"]+"\n")
        f.write("\n")
    print("Saved: "+out)
elif"/user/"in url:
    u=sp.user(eid)
    dn=u.get("display_name")or""
    un=u.get("id")
    fn=un if is_gibberish(dn)else dn
    fn=clean_name(fn)
    pls=sp.user_playlists(eid)
    b=os.path.join(base,"exports",fn+" - Playlists Overview.txt")
    f2=os.path.join(base,"exports",fn+" - Playlists Full Details.txt")
    link_full=os.path.join(base,"exports",fn+" - Playlists Full Details Links.txt")
    with open(b,"w",encoding="utf-8")as fb:
        write_header(fb,fn+" — Playlists Overview",u.get("external_urls",{}).get("spotify",""),None)
        for pl in pls["items"]:
            n=pl["name"]
            d=pl.get("description")or"(No Description)"
            fb.write("- "+n+"\n")
            fb.write("  "+d+"\n\n")
    print("Saved: "+b)
    with open(f2,"w",encoding="utf-8")as ff, open(link_full,"w",encoding="utf-8")as lf:
        write_header(ff,fn+" — Playlists Full Details",u.get("external_urls",{}).get("spotify",""),None)
        write_header(lf,fn+" — Playlists Full Details Links",u.get("external_urls",{}).get("spotify",""),None)
        for pl in pls["items"]:
            n=pl["name"]
            d=pl.get("description")or"(No Description)"
            ff.write("----------------------------------------\n")
            ff.write("Playlist: "+n+"\n")
            ff.write("Description: "+d+"\n\n")
            lf.write("----------------------------------------\n")
            lf.write("Playlist: "+n+"\n")
            lf.write("Description: "+d+"\n\n")
            pid=pl["id"]
            t=sp.playlist_tracks(pid)
            i=t.get("items",[])
            if not i:
                ff.write("(No Tracks)\n\n")
                lf.write("(No Tracks)\n\n")
                continue
            c=1
            while t:
                for item in t["items"]:
                    o=item["track"]
                    if o:
                        nm=o["name"]
                        a=", ".join(x["name"]for x in o["artists"])
                        url=o.get("external_urls", {}).get("spotify", "(No Link)")
                        ff.write(str(c)+". "+nm+" — "+a+"\n")
                        lf.write(url+"\n")
                        c+=1
                t=sp.next(t)if t["next"]else None
            ff.write("\n")
            lf.write("\n")
    print("Saved: "+f2)
    print("Saved links only: "+link_full)
else:
    print("Unsupported link.")
