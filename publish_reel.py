#!/usr/bin/env python3
"""Publication automatique des Reels Loucio sur Instagram (GitHub Actions).

File d'attente : reels/queue/<nom>.mp4 (+ <nom>.txt pour la légende).
Le plus ancien (ordre alphabétique) est publié au créneau de l'après-midi,
puis déplacé vers reels/published/. Un seul Reel par jour.
"""
import json, os, sys, time
from datetime import datetime

import publish  # réutilise token, api, wait_container, git_push, log
from publish import api, wait_container, git_push, log, RAW_BASE, PARIS

QUEUE = "reels/queue"
DONE = "reels/published"

DEFAULT_CAPTION = (
    "Un moment avec Loucio 🤍\n\n"
    "Ton compagnon spirituel qui t'écoute et prie avec toi. Lien en bio.\n\n"
    "#foi #prière #catholique #évangile #loucio"
)


def main():
    date = datetime.now(PARIS).strftime("%Y-%m-%d")

    state = json.load(open("state.json")) if os.path.exists("state.json") else {}
    if state.get(date, {}).get("reel"):
        log(f"{date} reel déjà publié, on sort")
        return

    videos = sorted(f for f in os.listdir(QUEUE) if f.lower().endswith(".mp4")) \
        if os.path.isdir(QUEUE) else []
    if not videos:
        log("file d'attente vide, rien à publier")
        return

    video = videos[0]
    base = video[:-4]
    txt = os.path.join(QUEUE, base + ".txt")
    caption = open(txt).read().strip() if os.path.exists(txt) else DEFAULT_CAPTION

    url = f"{RAW_BASE}/{QUEUE}/{video}"
    log(f"reel candidat : {video}")
    log("attente de la propagation de la vidéo (30s)…")
    time.sleep(30)

    res = api("POST", "me/media", media_type="REELS", video_url=url,
              caption=caption, share_to_feed="true")
    wait_container(res["id"], timeout=600)

    last_err = None
    for attempt in range(12):
        try:
            pub = api("POST", "me/media_publish", creation_id=res["id"])
            log(f"REEL PUBLIÉ ✔ media id {pub['id']}")
            break
        except RuntimeError as e:
            last_err = e
            log(f"média pas encore prêt (tentative {attempt+1}/12), nouvel essai dans 15s…")
            time.sleep(15)
    else:
        raise last_err

    os.makedirs(DONE, exist_ok=True)
    moved = []
    for src in (os.path.join(QUEUE, video), txt):
        if os.path.exists(src):
            dst = os.path.join(DONE, f"{date}-{os.path.basename(src)}")
            os.rename(src, dst)
            moved.append(dst)

    state.setdefault(date, {})["reel"] = pub["id"]
    json.dump(state, open("state.json", "w"), indent=2, ensure_ascii=False)
    git_push(["state.json", QUEUE, DONE], f"reel {date} publié ({video})")


if __name__ == "__main__":
    main()
