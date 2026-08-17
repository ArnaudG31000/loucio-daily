#!/usr/bin/env python3
"""Reels quotidiens Loucio : les carrousels matin/soir rendus en vidéo.

Slides FIXES (aucun zoom), fondus enchaînés doux, musique de fond
(assets/reel_music.mp3), format 9:16 (1080x1920) : la slide 4:5 est posée sur
un fond dégradé qui prolonge ses couleurs. Aucune dépendance IA : Pillow + ffmpeg.

Usage :
  python gen_reel.py 2026-08-18 matin out/2026-08-18-matin
  python gen_reel.py 2026-08-18 soir  out/2026-08-18-soir
"""
import json, os, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
import gen_carousel as gc
import gen_v2

FPS = 30
FADE = 0.6
RW, RH = 1080, 1920
MUSIC = "assets/reel_music.mp3"


def duration(text):
    words = len(str(text).split())
    return max(3.5, min(8.0, 2.0 + words / 2.6))


def pad_slide(src, dst):
    """Pose la slide 4:5 au centre d'un canevas 9:16, fond dégradé assorti."""
    img = Image.open(src).convert("RGB")
    w, h = img.size
    top = img.resize((1, 1), box=(0, 0, w, 2)).getpixel((0, 0))
    bot = img.resize((1, 1), box=(0, h - 2, w, h)).getpixel((0, 0))
    col = Image.new("RGB", (1, RH))
    for y in range(RH):
        t = y / (RH - 1)
        col.putpixel((0, y), tuple(int(top[i] + (bot[i] - top[i]) * t)
                                   for i in range(3)))
    canvas = col.resize((RW, RH))
    canvas.paste(img, ((RW - w) // 2, (RH - h) // 2))
    canvas.save(dst)


def make_clip(png, secs, out):
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1",
         "-framerate", str(FPS), "-t", f"{secs:.2f}", "-i", png,
         "-vf", f"scale={RW}:{RH},fps={FPS}",
         "-c:v", "libx264", "-preset", "fast", "-crf", "18",
         "-pix_fmt", "yuv420p", out], check=True)


def assemble(clips, durs, out, music=MUSIC):
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


def video_from_pngs(pngs, texts, outfile):
    durs = [duration(texts[i]) if i < len(texts) else 3.0
            for i in range(len(pngs))]
    with tempfile.TemporaryDirectory() as tmp:
        clips = []
        for i, p in enumerate(pngs):
            padded = os.path.join(tmp, f"pad_{i}.png")
            pad_slide(p, padded)
            c = os.path.join(tmp, f"clip_{i}.mp4")
            make_clip(padded, durs[i], c)
            clips.append(c)
        total = assemble(clips, durs, outfile)
    return total


def reel_for_slot(date, slot, outdir):
    """Génère le reel du créneau. Retourne (chemin_mp4, légende)."""
    os.makedirs(outdir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        if slot == "matin":
            c = json.load(open(f"content/gospel/{date}.json"))
            pngs = gc.build(c, tmp, theme=c.get("theme", "aube"))
            texts = [
                (c.get("question") or c["hook"]) + " " + c.get("saint", ""),
                c["hook"], c["gospel"], c["meditation_1"], c["meditation_2"],
                c.get("prayer", ""),
                c.get("cta_title", "") + " " + c.get("cta_sub", ""),
            ]
        else:
            c = json.load(open(f"content/evening/{date}.json"))
            pngs = gen_v2.render(c["slides"], tmp, c.get("theme", "nuit"))
            texts = [s.get("text", "") + " " + s.get("sub", "")
                     for s in c["slides"]]
        video = os.path.join(outdir, f"{date}-{slot}.mp4")
        total = video_from_pngs(pngs, texts, video)
    print(f"[gen_reel] ok {video} ({total:.1f}s)")
    return video, c["caption"]


if __name__ == "__main__":
    date, slot = sys.argv[1], sys.argv[2]
    outdir = sys.argv[3] if len(sys.argv) > 3 else f"out/reel/{date}-{slot}"
    reel_for_slot(date, slot, outdir)
