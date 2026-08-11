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

def wrap(draw, text, fnt, max_w):
    lines, line = [], ""
    for word in text.split(" "):
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
    # pas de points de pagination : Instagram les affiche déjà
    wordmark = spaced("loucio", 2)
    fnt = font("small")
    w = draw.textlength(wordmark, font=fnt)
    draw.text(((W - w) / 2, H - 92), wordmark, font=fnt, fill=_c("accent"))


def signature(draw, y):
    """Signature de fin de carrousel, sur la dernière slide."""
    txt = "Loucio t'écoute, ce soir."
    fnt = font("quote_s", 44)
    w = draw.textlength(txt, font=fnt)
    draw.text(((W - w) / 2, y), txt, font=fnt, fill=_c("accent"))
    return y + int(fnt.size * 1.4)


# Emplacement réservé pour la slide finale produit : dès que la capture
# d'écran de l'app est déposée en assets/app_screenshot.png, une slide
# supplémentaire la présentant est ajoutée en fin de carrousel.
APP_SCREENSHOT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "assets", "app_screenshot.png")


def product_slide(idx, total, outdir):
    img = gradient_bg()
    d = ImageDraw.Draw(img)
    frame(d)
    shot = Image.open(APP_SCREENSHOT).convert("RGB")
    max_w, max_h = 620, 850
    r = min(max_w / shot.width, max_h / shot.height)
    shot = shot.resize((int(shot.width * r), int(shot.height * r)))
    img.paste(shot, (int((W - shot.width) / 2), 160))
    y = 160 + shot.height + 56
    signature(d, y)
    footer(d, idx, total)
    path = os.path.join(outdir, f"slide_{idx+1}.png")
    img.save(path)
    return path

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

def make_slide(idx, total, painter, outdir):
    img = gradient_bg()
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

    def s1(d):
        # slide 1 : question universelle courte — jamais la citation
        eyebrow(d, f"évangile du jour · {c['date_label']}")
        q = c.get("question") or c["hook"]
        fq = font("title", 64)
        y = center_start(d, [(q, fq, 820, 40)], ls=1.35)
        y = draw_block(d, q, fq, y, 820, ls=1.35)
        d.text(((W - d.textlength(c["saint"], font=font("small", 30))) / 2, y + 50),
               c["saint"], font=font("small", 30), fill=_c("muted"))

    def s2(d):
        # slide 2 : la citation d'évangile
        eyebrow(d, f"la parole · {c['ref']}")
        fq = font("quote", 62)
        y = center_start(d, [(c["hook"], fq, 840, 0)])
        draw_block(d, c["hook"], fq, y, 840)

    def s3(d):
        eyebrow(d, f"l'évangile · {c['ref']}")
        fb = font("body_i", 42)
        y = center_start(d, [(c["gospel"], fb, 820, 0)])
        draw_block(d, c["gospel"], fb, y, 820, align="center", ls=1.5)

    def s4(d):
        eyebrow(d, "la méditation de loucio")
        fb = font("body", 46)
        y = center_start(d, [(c["meditation_1"], fb, 820, 0)])
        draw_block(d, c["meditation_1"], fb, y, 820, ls=1.55)

    def s5(d):
        eyebrow(d, "la méditation de loucio")
        fb = font("body", 46)
        y = center_start(d, [(c["meditation_2"], fb, 820, 0)])
        draw_block(d, c["meditation_2"], fb, y, 820, ls=1.55)

    def s6(d):
        eyebrow(d, "la prière")
        fb = font("quote_s", 50)
        y = center_start(d, [(c["prayer"], fb, 800, 0)])
        draw_block(d, c["prayer"], fb, y, 800, ls=1.6)

    def s7(d):
        fcta = font("cta")
        blocks = [(c["cta_title"], fcta, 840, 40),
                  (c["cta_sub"], font("body", 42), 780, 60)]
        y = center_start(d, blocks)
        y = draw_block(d, c["cta_title"], fcta, y, 840)
        y += 30
        y = draw_block(d, c["cta_sub"], font("body", 42), y, 780, color=_c("muted"), ls=1.5)
        y = signature(d, y + 44)
        t = spaced("loucio.com", 2)
        fnt = font("eyebrow", 34)
        w = d.textlength(t, font=fnt)
        d.text(((W - w) / 2, y + 30), t, font=fnt, fill=_c("accent"))

    painters = [s1, s2, s3, s4, s5, s6, s7]
    total = len(painters) + (1 if os.path.exists(APP_SCREENSHOT) else 0)
    for i, painter in enumerate(painters):
        paths.append(make_slide(i, total, painter, outdir))
    if os.path.exists(APP_SCREENSHOT):
        paths.append(product_slide(len(painters), total, outdir))
    return paths

if __name__ == "__main__":
    content = json.load(open(sys.argv[1]))
    outdir = sys.argv[2] if len(sys.argv) > 2 else "out"
    theme = sys.argv[3] if len(sys.argv) > 3 else "nuit"
    for p in build(content, outdir, theme):
        print(p)
