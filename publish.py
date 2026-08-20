#!/usr/bin/env python3
"""Publication automatique des carrousels Loucio sur Instagram (GitHub Actions)."""
import argparse, json, os, subprocess, sys, time
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

API = "https://graph.instagram.com/v23.0"
PARIS = ZoneInfo("Europe/Paris")


def _load_token():
    """Token courant : .automation/ig_token.enc (rafraîchi chaque semaine,
    chiffré avec le secret IG_TOKEN d'origine), sinon le secret d'amorce."""
    seed = os.environ["IG_TOKEN"]
    enc = ".automation/ig_token.enc"
    if os.path.exists(enc):
        try:
            out = subprocess.run(
                ["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2",
                 "-in", enc, "-pass", "env:IG_TOKEN"],
                capture_output=True, check=True)
            tok = out.stdout.decode().strip()
            if tok:
                return tok
        except subprocess.CalledProcessError:
            pass
    return seed


TOKEN = _load_token()
REPO = os.environ.get("GITHUB_REPOSITORY", "")
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/main"

def sh(*cmd):
    subprocess.run(cmd, check=True)

def log(msg):
    print(f"[loucio] {msg}", flush=True)

def api(method, path, **params):
    params["access_token"] = TOKEN
    r = requests.request(method, f"{API}/{path}", params=params, timeout=60)
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"Instagram API error on {path}: {data['error']}")
    return data

def wait_container(cid, timeout=240):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = api("GET", cid, fields="status_code").get("status_code")
        if st == "FINISHED":
            return
        if st == "ERROR":
            raise RuntimeError(f"container {cid} in ERROR state")
        time.sleep(5)
    raise RuntimeError(f"container {cid} not ready after {timeout}s")

def git_push(paths, message):
    sh("git", "config", "user.name", "loucio-bot")
    sh("git", "config", "user.email", "bot@loucio.com")
    sh("git", "add", *paths)
    r = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if r.returncode == 0:
        return
    sh("git", "commit", "-m", message)
    for attempt in range(3):
        try:
            sh("git", "pull", "--rebase")
            sh("git", "push")
            return
        except subprocess.CalledProcessError:
            time.sleep(5)
    raise RuntimeError("git push failed")

def publish_reel(video_path, caption):
    url = f"{RAW_BASE}/{video_path}"
    log(f"attente de la propagation de la vidéo (30s)… {url}")
    time.sleep(30)
    res = api("POST", "me/media", media_type="REELS", video_url=url,
              caption=caption, share_to_feed="true")
    wait_container(res["id"], timeout=600)
    last_err = None
    for attempt in range(12):
        try:
            pub = api("POST", "me/media_publish", creation_id=res["id"])
            log(f"REEL PUBLIÉ ✔ media id {pub['id']}")
            return pub["id"]
        except RuntimeError as e:
            last_err = e
            log(f"média pas encore prêt (tentative {attempt+1}/12), nouvel essai dans 15s…")
            time.sleep(15)
    raise last_err


def publish_carousel(image_paths, caption):
    log("attente de la propagation des images (30s)…")
    time.sleep(30)
    children = []
    for p in image_paths:
        url = f"{RAW_BASE}/{p}"
        log(f"container image: {url}")
        res = api("POST", "me/media", image_url=url, is_carousel_item="true")
        children.append(res["id"])
    for cid in children:
        wait_container(cid)
    log("container carrousel…")
    car = api("POST", "me/media", media_type="CAROUSEL",
              children=",".join(children), caption=caption)
    wait_container(car["id"])
    last_err = None
    for attempt in range(12):
        try:
            pub = api("POST", "me/media_publish", creation_id=car["id"])
            log(f"PUBLIÉ ✔ media id {pub['id']}")
            return pub["id"]
        except RuntimeError as e:
            last_err = e
            log(f"média pas encore prêt (tentative {attempt+1}/12), nouvel essai dans 15s…")
            time.sleep(15)
    raise last_err

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", default="auto")
    args = ap.parse_args()

    now = datetime.now(PARIS)
    slot = args.slot.strip()
    if slot == "auto":
        if 5 <= now.hour <= 10:
            slot = "matin"
        elif 19 <= now.hour <= 23:
            slot = "soir"
        else:
            log(f"hors créneau ({now:%H:%M} Paris), rien à faire")
            return
    date = f"{now:%Y-%m-%d}"

    state = json.load(open("state.json")) if os.path.exists("state.json") else {}
    if state.get(date, {}).get(slot):
        log(f"{date} {slot} déjà publié, on sort")
        return

    me = api("GET", "me", fields="username")
    log(f"compte connecté : @{me.get('username')}")

    outdir = f"out/{date}-{slot}"
    cpath = (f"content/gospel/{date}.json" if slot == "matin"
             else f"content/evening/{date}.json")
    if not os.path.exists(cpath):
        log(f"pas de contenu {cpath} — stock à recharger !")
        return
    import gen_reel
    video, caption = gen_reel.reel_for_slot(date, slot, outdir)

    git_push([outdir], f"reel {date} {slot}")
    media_id = publish_reel(video, caption)

    state.setdefault(date, {})[slot] = media_id
    json.dump(state, open("state.json", "w"), indent=2)
    git_push(["state.json"], f"état {date} {slot}")

if __name__ == "__main__":
    main()
