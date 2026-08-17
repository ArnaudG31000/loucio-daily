#!/usr/bin/env python3
"""Reel typographique quotidien : l'évangile du jour animé, dans le style des carrousels.

Usage :
  python gen_reel.py 2026-08-18                    # génère out/reel/2026-08-18/
  python gen_reel.py --auto                        # remplit reels/queue/ pour demain si vide

Le reel reprend le carrousel du matin (content/gospel/<date>.json) : hook question,
citation de l'évangile, deux méditations, appel à l'action. Zoom lent alterné,
fondus enchaînés, 1080x1920 30 fps. Aucune dépendance IA : Pillow + ffmpeg.
"""
import argparse, json, os, subprocess, sys, tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_carousel as gc
import gen_v2

FPS = 30
FADE = 0.5


def slides_from_gospel(g):
    return [
        {"type": "hook", "text": g["question"], "size": 64,
         "sub": f"Évangile du jour · {g.get('date_label', '')}"},
        {"type": "quote", "eyebrow": g.get("ref", "évangile"),
         "text": g["hook"], "size": 52},
        {"type": "body", "text": g["meditation_1"], "size": 46},
        {"type": "body", "text": g["meditation_2"], "size": 46},
        {"type": "cta", "text": g["cta_title"], "sub": g.get("cta_sub", "")},
    ]


def duration(text):
    words = len(text.split())
    return max(3.5, min(6.5, 2.0 + words / 2.6))


def make_clip(png, secs, zoom_in, out):
    frames = int(secs * FPS)
    z = (f"1+0.08*on/{frames}" if zoom_in else f"1.08-0.08*on/{frames}")
    vf = (f"scale=2160:3840,zoompan=z='{z}':x='(iw-iw/zoom)/2'"
          f":y='(ih-ih/zoom)/2':d=1:s=1080x1920:fps={FPS}")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1",
         "-framerate", str(FPS), "-t", f"{secs:.2f}", "-i", png,
         "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "18",
         "-pix_fmt", "yuv420p", out], check=True)


def assemble(clips, durs, out, music=None):
    args = ["ffmpeg", "-y", "-loglevel", "error"]
    for c in clips:
        args += ["-i", c]
    graph, prev, total = [], "0:v", durs[0]
    for i in range(1, len(clips)):
        offset = total - FADE
        lbl = f"v{i}"
        graph.append(f"[{prev}][{i}:v]xfade=transition=fade"
                     f":duration={FADE}:offset={offset:.2f}[{lbl}]")
        prev, total = lbl, offset + durs[i]
    fg = ";".join(graph) if graph else None
    if music and os.path.exists(music):
        args += ["-stream_loop", "-1", "-i", music]
        aidx = len(clips)
        af = (f"[{aidx}:a]volume=0.25,afade=t=in:d=1,"
              f"afade=t=out:st={total-2:.2f}:d=2[aout]")
        fg = (fg + ";" + af) if fg else af
        args += ["-filter_complex", fg, "-map", f"[{prev}]", "-map", "[aout]",
                 "-t", f"{total:.2f}", "-c:a", "aac", "-b:a", "128k"]
    elif fg:
        args += ["-filter_complex", fg, "-map", f"[{prev}]"]
    args += ["-c:v", "libx264", "-preset", "medium", "-crf", "19",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    subprocess.run(args, check=True)
    return total


def generate(date, outdir):
    src = f"content/gospel/{date}.json"
    g = json.load(open(src))
    os.makedirs(outdir, exist_ok=True)
    slides = slides_from_gospel(g)
    with tempfile.TemporaryDirectory() as tmp:
        pngs = gen_v2.render(slides, tmp, theme=g.get("theme", "aube"))
        durs = [duration(s.get("text", "") + " " + s.get("sub", ""))
                for s in slides]
        durs += [3.0] * (len(pngs) - len(slides))  # slide produit éventuelle
        clips = []
        for i, p in enumerate(pngs):
            c = os.path.join(tmp, f"clip_{i}.mp4")
            make_clip(p, durs[i], zoom_in=(i % 2 == 0), out=c)
            clips.append(c)
        video = os.path.join(outdir, f"{date}-evangile.mp4")
        total = assemble(clips, durs, video, music="assets/reel_music.mp3")
    caption = g.get("caption", "")
    cap_path = os.path.join(outdir, f"{date}-evangile.txt")
    open(cap_path, "w").write(caption)
    print(f"ok {video} ({total:.1f}s)")
    return video, cap_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date", nargs="?")
    ap.add_argument("--auto", action="store_true",
                    help="génère le reel de demain dans reels/queue/ si la file est vide")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.auto:
        queue = "reels/queue"
        pending = [f for f in os.listdir(queue) if f.endswith(".mp4")] \
            if os.path.isdir(queue) else []
        if pending:
            print("file non vide, pas de génération")
            return
        from zoneinfo import ZoneInfo
        date = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d")
        if not os.path.exists(f"content/gospel/{date}.json"):
            print(f"pas de contenu pour {date}, abandon")
            return
        generate(date, queue)
    else:
        date = a.date or datetime.now().strftime("%Y-%m-%d")
        generate(date, a.out or f"out/reel/{date}")


if __name__ == "__main__":
    main()
