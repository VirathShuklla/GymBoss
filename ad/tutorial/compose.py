import asyncio
import bisect
import json
import subprocess
import sys
import wave
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageFilter
from playwright.async_api import async_playwright

from steps import CHAPTERS

ROOT = Path(__file__).parent
FF = imageio_ffmpeg.get_ffmpeg_exe()
FPS, W, H, K = 25, 1920, 1080, 4 / 3
CARD, INTRO, OUTRO = 2.8, 4.2, 4.5
OV = ROOT / "ov"
OUT = ROOT / "out"
SR = 24000
FONTS = '<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@500;700;800&family=JetBrains+Mono:wght@700&display=block" rel="stylesheet">'
CSS = """*{margin:0;padding:0;box-sizing:border-box}body{background:transparent;font-family:Outfit}
.cap{display:inline-flex;flex-direction:column;gap:6px;background:rgba(15,10,30,.88);border:1.5px solid rgba(167,139,250,.45);border-radius:22px;padding:18px 34px;box-shadow:0 18px 40px rgba(0,0,0,.35)}
.cap .k{font:700 19px Outfit;letter-spacing:3px;color:#A78BFA;text-transform:uppercase}.cap .t{font:700 38px Outfit;color:#fff}
.card{width:1920px;height:1080px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;color:#fff;text-align:center}
.card .n{font:700 30px 'JetBrains Mono';letter-spacing:8px;color:#C6FF3D}.card .t{font:800 104px Outfit;line-height:1.05;text-shadow:0 8px 30px rgba(0,0,0,.4)}
.card .s{font:500 36px Outfit;color:rgba(255,255,255,.8)}.card .logo{font:800 40px Outfit;margin-top:26px;letter-spacing:1px}.card .logo b{color:#A78BFA}
"""


async def overlays():
    OV.mkdir(exist_ok=True)
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        pg = await b.new_page(viewport={"width": W, "height": H})

        async def shot(html, path, sel):
            await pg.set_content(f'<html><head><meta charset="utf-8">{FONTS}<style>{CSS}</style></head><body>{html}</body></html>', wait_until="networkidle")
            await pg.evaluate("document.fonts.ready")
            await pg.locator(sel).screenshot(path=str(path), omit_background=True)
        logo = '<div class="logo">GymBoss<b>_VVO</b></div>'
        for ci, ch in enumerate(CHAPTERS):
            for s in ch["steps"]:
                await shot(f'<div class="cap"><span class="k">Chapter {ci + 1} · {ch["title"]}</span><span class="t">{s["cap"]}</span></div>', OV / f"cap_{s['id']}.png", ".cap")
            await shot(f'<div class="card"><div class="n">CHAPTER {ci + 1:02d}</div><div class="t">{ch["title"]}</div>{logo}</div>', OV / f"card_{ci}.png", ".card")
        await shot(f'<div class="card"><div class="n">GYMBOSS TUTORIAL</div><div class="t">Run your gym<br>with GymBoss</div><div class="s">A full day at the gym, step by step</div>{logo}</div>', OV / "card_intro.png", ".card")
        await shot(f'<div class="card"><div class="n">YOU\'RE ALL SET</div><div class="t">Start your<br>free trial</div><div class="s">gymbossvvo.in</div>{logo}</div>', OV / "card_outro.png", ".card")
        await b.close()


def timeline():
    d = json.loads((ROOT / "rec.json").read_text())
    log, frames = d["log"], d["frames"]
    chs = [e for e in log if e["kind"] == "chapter"]
    end_t = [e["t"] for e in log if e["kind"] == "end"][0]
    pieces, t_out = [("card", "intro", INTRO)], INTRO
    rec_map, chapter_out = [], []
    for i, c in enumerate(chs):
        a = c["t"]
        b = chs[i + 1]["t"] if i + 1 < len(chs) else end_t
        chapter_out.append([c["n"], c["title"], t_out])
        if i > 0:
            pieces.append(("card", c["n"], CARD))
            t_out += CARD
        pieces.append(("rec", a, b))
        rec_map.append((t_out, a, b))
        t_out += b - a
        chapter_out[-1].append(t_out)
    pieces.append(("card", "outro", OUTRO))
    chapter_out[0][2] = 0.0
    total = t_out + OUTRO
    return d, pieces, rec_map, chapter_out, total


def rec_to_out(rec_map, t):
    for o, a, b in rec_map:
        if a <= t <= b:
            return o + t - a
    return None


def zoom_track(log, n_rec, dt):
    tgt = np.tile([1.0, W / 2, H / 2], (n_rec, 1))
    for e in log:
        if e["kind"] != "zoom":
            continue
        x, y, w, h = [v * K for v in e["rect"]]
        s = float(np.clip(min(W / max(w, 1), H / max(h, 1)), 1.0, 1.75))
        i0, i1 = int(e["t"] / dt), int((e["t"] + e["dur"]) / dt)
        tgt[i0:i1] = [s, x + w / 2, y + h / 2]
    st = np.empty_like(tgt)
    cur = tgt[0].copy()
    for i in range(n_rec):
        cur += (tgt[i] - cur) * 0.085
        st[i] = cur
    return st


def crop_box(s, cx, cy):
    w, h = W / s, H / s
    x = float(np.clip(cx - w / 2, 0, W - w))
    y = float(np.clip(cy - h / 2, 0, H - h))
    return (x, y, x + w, y + h)


def render_chunk(args):
    idx, f0, f1 = args
    d, pieces, rec_map, chapter_out, total = timeline()
    log, frames = d["log"], d["frames"]
    dt = 1 / FPS
    n_rec = int(log[-1]["t"] / dt) + 2
    zt = zoom_track(log, n_rec, dt)
    steps = [e for e in log if e["kind"] in ("step", "step_end")]
    caps = {}
    for e in steps:
        if e["kind"] == "step":
            caps.setdefault(e["id"], [e["t"], None])
        else:
            caps[e["id"]][1] = e["t"]
    capimg = {k: Image.open(OV / f"cap_{k}.png").convert("RGBA") for k in caps}
    starts = [(pc, (sum(p[2] if p[0] == "card" else p[2] - p[1] for p in pieces[:i]))) for i, pc in enumerate(pieces)]
    out = OUT / f"chunk_{idx:03d}.mp4"
    proc = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                             "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-tune", "stillimage", str(out)], stdin=subprocess.PIPE)
    cache = {}

    def frame(j):
        if j not in cache:
            cache.clear()
            cache[j] = Image.open(ROOT / "frames" / f"{j:06d}.jpg").convert("RGB")
        return cache[j]

    def card_bg(rec_t, key):
        k = ("bg", key)
        if k not in cache:
            j = max(0, bisect.bisect_right(frames, rec_t) - 1)
            im = Image.open(ROOT / "frames" / f"{j:06d}.jpg").convert("RGB").filter(ImageFilter.GaussianBlur(22))
            im = Image.blend(im, Image.new("RGB", (W, H), (24, 12, 52)), 0.62)
            cache.clear()
            cache[k] = im
        return cache[k]
    cards = {}
    for fi in range(f0, f1):
        T = fi * dt
        for (pc, s0) in reversed(starts):
            if T >= s0:
                break
        if pc[0] == "card":
            key, dur = pc[1], pc[2]
            lt = T - s0
            nxt = starts[[p for p, _ in starts].index(pc) + 1][0] if key != "outro" else None
            prv = starts[[p for p, _ in starts].index(pc) - 1][0] if key != "intro" else None
            rec_t = nxt[1] if nxt else prv[2] - 0.1
            img = card_bg(rec_t, key).copy()
            if key not in cards:
                cards[key] = Image.open(OV / f"card_{key}.png").convert("RGBA")
            a = min(1, lt / 0.35, (dur - lt) / 0.35)
            ov = cards[key]
            if a < 1:
                ov = ov.copy()
                ov.putalpha(ov.getchannel("A").point(lambda v: int(v * a)))
            img.paste(ov, (0, 0), ov)
        else:
            rt = pc[1] + (T - s0)
            j = max(0, bisect.bisect_right(frames, rt) - 1)
            s, cx, cy = zt[min(int(rt / dt), n_rec - 1)]
            src = frame(j)
            img = src.resize((W, H), Image.BILINEAR, box=crop_box(s, cx, cy)) if s > 1.01 else src.copy()
            for k, (a, b) in caps.items():
                if a <= rt <= (b or 1e9):
                    ci = capimg[k]
                    al = min(1, (rt - a) / 0.3, ((b or 1e9) - rt) / 0.25)
                    if al < 1:
                        ci = ci.copy()
                        ci.putalpha(ci.getchannel("A").point(lambda v: int(v * max(al, 0))))
                    img.paste(ci, ((W - ci.width) // 2, H - ci.height - 34), ci)
                    break
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    return idx


def read24(p):
    raw = Path(p).read_bytes()
    return np.frombuffer(raw[44:][: (len(raw) - 44) // 2 * 2], dtype=np.int16).astype(np.float32) / 32768


def audio(d, rec_map, total):
    n = int(total * SR)
    out = np.zeros(n, np.float32)
    t = np.arange(int(0.05 * SR)) / SR
    click = (np.sin(2 * np.pi * 1900 * t) * np.exp(-t * 120)).astype(np.float32) * 0.12
    for e in d["log"]:
        o = rec_to_out(rec_map, e["t"])
        if o is None:
            continue
        i = int(o * SR)
        if e["kind"] == "step":
            v = read24(ROOT / "vo" / f"{e['id']}.wav")
            v = v / (np.abs(v).max() + 1e-9) * 0.85
            v = v[: n - i]
            out[i:i + len(v)] += v
        elif e["kind"] == "click":
            c = click[: n - i]
            out[i:i + len(c)] += c
    out = np.clip(out, -1, 1)
    p = OUT / "audio.wav"
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 32767).astype(np.int16).tobytes())
    return p


def srt(d, rec_map, chapter_out):
    vo = {s["id"]: s["vo"] for ch in CHAPTERS for s in ch["steps"]}
    durs = json.loads((ROOT / "vo_durs.json").read_text())
    fmt = lambda x: f"{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(x % 1 * 1000):03d}"
    lines, k = [], 1
    for e in d["log"]:
        if e["kind"] == "step":
            o = rec_to_out(rec_map, e["t"])
            lines.append(f"{k}\n{fmt(o)} --> {fmt(o + durs[e['id']])}\n{vo[e['id']]}\n")
            k += 1
    (OUT / "GymBoss_Tutorial.srt").write_text("\n".join(lines))
    chap = "\n".join(f"{int(a // 60):02d}:{int(a % 60):02d} {t}" for _, t, a, _ in chapter_out)
    (OUT / "chapters.txt").write_text(chap)
    print(chap)


def main():
    OUT.mkdir(exist_ok=True)
    asyncio.run(overlays())
    d, pieces, rec_map, chapter_out, total = timeline()
    nf = int(total * FPS)
    W_ = 4
    bounds = np.linspace(0, nf, W_ + 1).astype(int)
    with ProcessPoolExecutor(W_) as ex:
        list(ex.map(render_chunk, [(i, bounds[i], bounds[i + 1]) for i in range(W_)]))
    (OUT / "list.txt").write_text("".join(f"file 'chunk_{i:03d}.mp4'\n" for i in range(W_)))
    a = audio(d, rec_map, total)
    final = OUT / "GymBoss_Full_Tutorial_16x9.mp4"
    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(OUT / "list.txt"), "-i", str(a), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(final)], check=True)
    srt(d, rec_map, chapter_out)
    clips = OUT / "clips"
    clips.mkdir(exist_ok=True)
    for n, title, a0, a1 in chapter_out:
        name = f"{n + 1:02d}_{title.replace(' ', '_').replace('&', 'and')}.mp4"
        end = a1 + (OUTRO if n == chapter_out[-1][0] else 0)
        subprocess.run([FF, "-y", "-loglevel", "error", "-ss", f"{a0:.3f}", "-i", str(final), "-t", f"{end - a0:.3f}", "-c:v", "libx264", "-preset", "medium",
                        "-crf", "19", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(clips / name)], check=True)
    for f in OUT.glob("chunk_*.mp4"):
        f.unlink()
    print("DONE", final, round(total, 1))


if __name__ == "__main__":
    main()
