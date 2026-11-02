import asyncio
import subprocess
import sys
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from playwright.async_api import async_playwright

ROOT = Path(__file__).parent
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
SR = 44100


def read_voice(slug):
    raw = (ROOT / "audio" / f"{slug}.wav").read_bytes()[44:]
    x = np.frombuffer(raw[: len(raw) // 2 * 2], dtype=np.int16).astype(np.float32) / 32768
    src_t = np.arange(len(x)) / 24000
    dst_t = np.arange(int(len(x) / 24000 * SR)) / SR
    return np.interp(dst_t, src_t, x)


def mix_audio(total, vo, out):
    subprocess.run([sys.executable, str(ROOT / "music.py"), str(total), str(ROOT / "audio" / "music.wav")], check=True)
    with wave.open(str(ROOT / "audio" / "music.wav")) as w:
        music = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    n = int(total * SR)
    music = np.pad(music, (0, max(0, n - len(music))))[:n]
    voice = np.zeros(n, dtype=np.float32)
    for slug, at in vo:
        v = read_voice(slug)
        i = int(at * SR)
        v = v[: n - i]
        voice[i:i + len(v)] += v
    act = np.convolve(np.abs(voice), np.ones(2205) / 2205, mode="same") > 0.01
    duck = np.convolve(act.astype(np.float32), np.ones(8820) / 8820, mode="same")
    music_gain = 0.5 - 0.36 * np.clip(duck * 1.5, 0, 1)
    voice = voice / (np.abs(voice).max() + 1e-9) * 0.95
    mix = music * music_gain + voice
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    data = (mix / (np.abs(mix).max() + 1e-9) * 0.95 * 32767).astype(np.int16)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


async def render(fmt, preview_times=None):
    W, H = (1080, 1920) if fmt == "vertical" else (1920, 1080)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        page = await b.new_page(viewport={"width": W, "height": H})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        await page.goto(f"file://{ROOT}/ad.html?fmt={fmt}")
        await page.evaluate("window.READY")
        await page.wait_for_timeout(800)
        tl = await page.evaluate("window.TIMELINE")
        if errors:
            print("JS ERRORS", errors)
        if preview_times is not None:
            for t in preview_times:
                await page.evaluate(f"render({t})")
                await page.screenshot(path=str(ROOT / "preview" / f"{fmt}_{t:05.2f}.jpg"), type="jpeg", quality=60)
            await b.close()
            return
        total = tl["total"]
        silent = ROOT / "out" / f"{fmt}_video.mp4"
        proc = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                                 "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(silent)], stdin=subprocess.PIPE)
        for i in range(int(total * FPS)):
            await page.evaluate(f"render({i / FPS})")
            proc.stdin.write(await page.screenshot(type="jpeg", quality=93))
            if i % 150 == 0:
                print(fmt, "frame", i, flush=True)
        proc.stdin.close()
        proc.wait()
        await b.close()
    audio = ROOT / "out" / f"{fmt}_audio.wav"
    mix_audio(total, tl["vo"], audio)
    final = ROOT / "out" / f"GymBoss_Ad_{'16x9_30s' if fmt == 'wide' else '9x16_20s'}.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(silent), "-i", str(audio), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(final)], check=True)
    print("DONE", final)


if __name__ == "__main__":
    fmt = sys.argv[1]
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "preview").mkdir(exist_ok=True)
    times = [float(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else None
    asyncio.run(render(fmt, times))
