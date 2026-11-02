import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

SRC = Path(__file__).parent / "assets"
OUT = SRC / "cut"
OUT.mkdir(exist_ok=True)


def checker_model(gray, bg):
    vals = gray[bg]
    hi, lo = np.percentile(vals, 85), np.percentile(vals, 15)
    if hi - lo < 12:
        return None
    h, w = gray.shape
    ys, xs = np.nonzero(bg)
    pick = np.random.default_rng(0).choice(len(ys), min(20000, len(ys)), replace=False)
    ys, xs = ys[pick], xs[pick]
    tone = gray[ys, xs] > (hi + lo) / 2
    best = (0, None)
    for s in range(8, 65):
        for ox in range(0, s * 2, 2):
            for oy in (0, s):
                m = ((((xs + ox) // s + (ys + oy) // s) % 2) == 0) == tone
                score = max(m.mean(), 1 - m.mean())
                if score > best[0]:
                    best = (score, (s, ox, oy, m.mean() >= 0.5))
    print("checker", round(best[0], 3), best[1])
    if best[0] < 0.85:
        return None
    s, ox, oy, same = best[1]
    yy, xx = np.mgrid[0:h, 0:w]
    pat = (((xx + ox) // s + (yy + oy) // s) % 2) == 0
    return np.where(pat == same, hi, lo)

for f in sorted(SRC.glob("panda_*.jpg")):
    a = np.asarray(Image.open(f).convert("RGB")).astype(np.int16)
    mx, mn = a.max(2), a.min(2)
    light = (mn > 175) & (mx - mn < 22)
    lab, _ = ndimage.label(light)
    edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    bg = np.isin(lab, edge[edge > 0])
    gray = a.mean(2)
    exp = checker_model(gray, bg)
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        comp = lab[sl] == i
        if exp is not None and comp.sum() > 800 and not bg[sl][comp].any():
            if (np.abs(gray[sl][comp] - exp[sl][comp]) < 14).mean() > 0.8:
                bg[sl] |= comp
    bg = ndimage.binary_opening(bg, iterations=1)
    fg = ndimage.binary_opening(~bg, iterations=2)
    fg = ndimage.binary_fill_holes(ndimage.binary_opening(fg, iterations=2)) if "--fill" in sys.argv else fg
    keep, n = ndimage.label(fg)
    if n > 1:
        sizes = ndimage.sum(fg, keep, range(1, n + 1))
        fg = np.isin(keep, [i + 1 for i, s in enumerate(sizes) if s > 0.01 * fg.sum()])
    alpha = Image.fromarray((fg * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    img = Image.open(f).convert("RGB")
    img.putalpha(alpha)
    img = img.crop(img.getbbox())
    img.save(OUT / (f.stem + ".png"))
    print(f.stem, img.size)

prev = Image.new("RGB", (1600, 420), (40, 16, 80))
x = 0
for p in sorted(OUT.glob("*.png")):
    im = Image.open(p)
    im.thumbnail((200, 400))
    prev.paste(im, (x, 10), im)
    x += 200
prev.save(SRC / "preview.png")
