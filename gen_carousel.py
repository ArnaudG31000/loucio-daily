#!/usr/bin/env python3
"""
Générateur de carrousels Loucio — cœur graphique avec thèmes.
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350

THEMES = {
    "nuit": {   # bleu nuit — le thème historique
        "bg_top": (14, 22, 40), "bg_bot": (24, 36, 62),
        "text": (245, 239, 226), "accent": (201, 164, 92), "muted": (170, 178, 195),
    },
    "aube": {   # crème chaud, texte bleu nuit, accent terracotta
        "bg_top": (247, 241, 230), "bg_bot": (238, 226, 205),
        "text": (28, 38, 60), "accent": (183, 110, 74), "muted": (120, 118, 110),
    },
    "lumiere": {  # doré doux, texte brun profond
        "bg_top": (242, 230, 205), "bg_bot": (224, 202, 160),
        "text": (58, 42, 28), "accent": (146, 100, 40), "muted": (130, 112, 88),
    },
    "sauge": {  # vert sauge apaisant, texte crème
        "bg_top": (44, 58, 50), "bg_bot": (62, 82, 70),
        "text": (240, 238, 226), "accent": (196, 178, 118), "muted": (168, 180, 168),
    },
}
THEME = dict(THEMES["nuit"])

def set_theme(name):
    THEME.clear(); THEME.update(THEMES[name])

# rétro-compatibilité (anciennes constantes)
def _c(k): return THEME[k]

F = "/usr/share/fonts/truetype/"
FONTS = {
    "quote":   (F + "liberation/LiberationSerif-Italic.ttf", 64),
    "quote_s": (F + "liberation/LiberationSerif-Italic.ttf", 54),
    "title":   (F + "dejavu/DejaVuSerif-Bold.ttf", 58),
    "body":    (F + "liberation/LiberationSerif-Regular.ttf", 44),
    "body_i":  (F + "liberation/LiberationSerif-Italic.ttf", 44),
    "eyebrow": (F + "dejavu/DejaVuSans.ttf", 30),
    "small":   (F + "dejavu/DejaVuSans.ttf", 26),
    "cta":     (F + "dejavu/DejaVuSerif-Bold.ttf", 66),
}

def font(k, size=None):
    path, s = FONTS[k]
    return ImageFont.truetype(path, size or s)

def gradient_bg():
    img = Image.new("RGB", (W, H))
    top, bot = _c("bg_top"), _c("bg_bot")
    for y in range(H):
        t = y / H
        c = tuple(int(a + (b - a) * t) for a, b in zip(top, bot))
        img.paste(Image.new("RGB", (W, 1), c), (0, y))
    return img

def clean(text):
    # les polices n'ont pas de glyphes emoji (carré vide) — on les retire des slides
    out = "".join(ch for ch in text
                  if (ord(ch) < 0x2600 or (0x27C0 <= ord(ch) < 0x1F000))
                  and ord(ch) != 0xFE0F)
    return " ".join(out.split())

def wrap(draw, text, fnt, max_w):
    lines, line = [], ""
    for word in clean(text).split(" "):
        test = (line + " " + word).strip()
        if draw.textlength(test, font=fnt) <= max_w:
            line = test
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    return lines

def draw_block(draw, text, fnt, y, max_w, color=None, align="center", ls=1.45):
    color = color or _c("text")
    lines = wrap(draw, text, fnt, max_w)
    lh = int(fnt.size * ls)
    for ln in lines:
        w = draw.textlength(ln, font=fnt)
        x = (W - w) / 2 if align == "center" else (W - max_w) / 2
        draw.text((x, y), ln, font=fnt, fill=color)
        y += lh
    return y

def spaced(s, n=3):
    return (" " * n).join(list(s.upper()))

def frame(draw):
    m = 42
    draw.rectangle([m, m, W - m, H - m], outline=_c("accent"), width=2)

def footer(draw, idx, total):
    # pas de points de pagination : Instagram affiche déjà les siens
    wordmark = spaced("loucio", 2)
    fnt = font("small")
    w = draw.textlength(wordmark, font=fnt)
    draw.text(((W - w) / 2, H - 96), wordmark, font=fnt, fill=_c("accent"))

APP_SCREENSHOT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "assets", "app_screenshot.png")

def signature(draw, y, img=None):
    """Signature de fin de carrousel. Déposer assets/app_screenshot.png pour
    insérer le visuel de l'app au-dessus de la signature (slide produit)."""
    if img is not None and os.path.exists(APP_SCREENSHOT):
        shot = Image.open(APP_SCREENSHOT).convert("RGBA")
        max_w, max_h = 420, H - 240 - int(y)
        if max_h > 200:
            ratio = min(max_w / shot.width, max_h / shot.height)
            shot = shot.resize((int(shot.width * ratio), int(shot.height * ratio)))
            img.paste(shot, (int((W - shot.width) / 2), int(y)), shot)
            y += shot.height + 40
    t = "Loucio t'écoute, ce soir."
    fnt = font("quote_s", 46)
    w = draw.textlength(t, font=fnt)
    draw.text(((W - w) / 2, y), t, font=fnt, fill=_c("accent"))
    return y + int(fnt.size * 1.5)

def eyebrow(draw, text, y=150):
    for gap, size in [(2, 30), (1, 30), (1, 26), (0, 26), (0, 22)]:
        fnt = font("eyebrow", size)
        t = spaced(text, gap) if gap else text.upper()
        if draw.textlength(t, font=fnt) <= 900:
            break
    w = draw.textlength(t, font=fnt)
    draw.text(((W - w) / 2, y), t, font=fnt, fill=_c("accent"))
    draw.line([(W/2 - 40, y + 58), (W/2 + 40, y + 58)], fill=_c("accent"), width=2)

def center_start(draw, blocks, ls=1.45):
    total = 0
    for text, fnt, max_w, gap in blocks:
        lines = wrap(draw, text, fnt, max_w)
        total += len(lines) * int(fnt.size * ls) + gap
    return max(240, (H - total) / 2)

CURRENT_IMG = None

def make_slide(idx, total, painter, outdir):
    global CURRENT_IMG
    img = gradient_bg()
    CURRENT_IMG = img
    draw = ImageDraw.Draw(img)
    frame(draw)
    painter(draw)
    footer(draw, idx, total)
    path = os.path.join(outdir, f"slide_{idx+1}.png")
    img.save(path)
    return path

def build(content, outdir, theme="nuit"):
    set_theme(theme)
    os.makedirs(outdir, exist_ok=True)
    c = content
    paths = []
    total = 6

    def s1(d):
        # slide 1 : question universelle qui accroche — jamais la citation
        eyebrow(d, f"évangile du jour · {c['date_label']}")
        question = c.get("question") or c["hook"]
        fq = font("cta", 62)
        y = center_start(d, [(question, fq, 840, 40)])
        y = draw_block(d, question, fq, y, 840)
        d.text(((W - d.textlength(c["saint"], font=font("small", 30))) / 2, y + 50),
               c["saint"], font=font("small", 30), fill=_c("muted"))

    def s2(d):
        eyebrow(d, f"l'évangile · {c['ref']}")
        fb = font("body_i", 42)
        y = center_start(d, [(c["gospel"], fb, 820, 0)])
        draw_block(d, c["gospel"], fb, y, 820, align="center", ls=1.5)

    def s3(d):
        eyebrow(d, "la méditation de loucio")
        fb = font("body", 46)
        y = center_start(d, [(c["meditation_1"], fb, 820, 0)])
        draw_block(d, c["meditation_1"], fb, y, 820, ls=1.55)

    def s4(d):
        eyebrow(d, "la méditation de loucio")
        fb = font("body", 46)
        y = center_start(d, [(c["meditation_2"], fb, 820, 0)])
        draw_block(d, c["meditation_2"], fb, y, 820, ls=1.55)

    def s5(d):
        eyebrow(d, "la prière")
        fb = font("quote_s", 50)
        y = center_start(d, [(c["prayer"], fb, 800, 0)])
        draw_block(d, c["prayer"], fb, y, 800, ls=1.6)

    def s6(d):
        fcta = font("cta")
        blocks = [(c["cta_title"], fcta, 840, 40),
                  (c["cta_sub"], font("body", 42), 780, 60)]
        y = center_start(d, blocks)
        y = draw_block(d, c["cta_title"], fcta, y, 840)
        y += 30
        y = draw_block(d, c["cta_sub"], font("body", 42), y, 780, color=_c("muted"), ls=1.5)
        y = signature(d, y + 55, CURRENT_IMG)
        t = spaced("loucio.com", 2)
        fnt = font("eyebrow", 34)
        w = d.textlength(t, font=fnt)
        d.text(((W - w) / 2, y + 25), t, font=fnt, fill=_c("accent"))

    for i, painter in enumerate([s1, s2, s3, s4, s5, s6]):
        paths.append(make_slide(i, total, painter, outdir))
    return paths

if __name__ == "__main__":
    content = json.load(open(sys.argv[1]))
    outdir = sys.argv[2] if len(sys.argv) > 2 else "out"
    theme = sys.argv[3] if len(sys.argv) > 3 else "nuit"
    for p in build(content, outdir, theme):
        print(p)
