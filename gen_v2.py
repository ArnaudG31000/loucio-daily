#!/usr/bin/env python3
"""Générateur v2 — carrousels à architecture libre, avec thèmes."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_carousel as gc
from PIL import Image, ImageDraw

W, H = gc.W, gc.H

def render(slides, outdir, theme="nuit"):
    gc.set_theme(theme)
    os.makedirs(outdir, exist_ok=True)
    total = len(slides)
    paths = []
    for i, s in enumerate(slides):
        img = gc.gradient_bg()
        d = ImageDraw.Draw(img)
        gc.frame(d)
        t = s["type"]
        if t == "hook":
            if s.get("eyebrow"): gc.eyebrow(d, s["eyebrow"])
            fq = gc.font("quote", s.get("size", 68))
            y = gc.center_start(d, [(s["text"], fq, 840, 40)])
            y = gc.draw_block(d, s["text"], fq, y, 840)
            if s.get("sub"):
                y += 40
                gc.draw_block(d, s["sub"], gc.font("small", 32), y, 700,
                              color=gc.THEME["muted"], ls=1.4)
        elif t == "body":
            if s.get("eyebrow"): gc.eyebrow(d, s["eyebrow"])
            fb = gc.font("body", s.get("size", 48))
            y = gc.center_start(d, [(s["text"], fb, 800, 0)])
            gc.draw_block(d, s["text"], fb, y, 800, ls=1.55)
        elif t == "quote":
            if s.get("eyebrow"): gc.eyebrow(d, s["eyebrow"])
            fb = gc.font("body_i", s.get("size", 44))
            y = gc.center_start(d, [(s["text"], fb, 810, 0)])
            gc.draw_block(d, s["text"], fb, y, 810, ls=1.5)
        elif t == "punch":
            fp = gc.font("title", s.get("size", 62))
            y = gc.center_start(d, [(s["text"], fp, 820, 0)])
            gc.draw_block(d, s["text"], fp, y, 820, ls=1.4)
        elif t == "cta":
            fcta = gc.font("cta", 60)
            y = gc.center_start(d, [(s["text"], fcta, 840, 40),
                                    (s.get("sub", ""), gc.font("body", 42), 780, 60)])
            y = gc.draw_block(d, s["text"], fcta, y, 840)
            if s.get("sub"):
                y += 30
                y = gc.draw_block(d, s["sub"], gc.font("body", 42), y, 780,
                                  color=gc.THEME["muted"], ls=1.5)
            tt = gc.spaced("loucio.com", 2)
            fnt = gc.font("eyebrow", 34)
            d.text(((W - d.textlength(tt, font=fnt)) / 2, y + 60), tt,
                   font=fnt, fill=gc.THEME["accent"])
        gc.footer(d, i, total)
        p = os.path.join(outdir, f"slide_{i+1}.png")
        img.save(p); paths.append(p)
    return paths

if __name__ == "__main__":
    spec = json.load(open(sys.argv[1]))
    theme = sys.argv[3] if len(sys.argv) > 3 else "nuit"
    render(spec["slides"], sys.argv[2], theme)
    print("ok", sys.argv[2])
