import subprocess
import sys
import wave

import numpy as np

from pg_render import EPS, OUT, ROOT, S, X, FF, SR, read_wav

VOICE_FX = "highpass=f=75,lowpass=f=13000,equalizer=f=180:t=q:w=1:g=1.5,equalizer=f=3200:t=q:w=1.2:g=2.5,deesser=i=0.4,acompressor=threshold=-30dB:ratio=4:attack=5:release=150:makeup=4,alimiter=limit=0.9:attack=3:release=60,aecho=0.85:0.4:35:0.08"


def smooth(x, k):
    c = np.cumsum(np.concatenate([np.zeros(k // 2 + 1), x, np.zeros(k // 2)]))
    return (c[k:] - c[:-k])[: len(x)] / k


def write(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def remix(n):
    cfg = EPS[n]
    total = S[4] + cfg["end_dur"]
    N = int(total * SR)
    fit = lambda x: np.pad(x, (0, max(0, N - len(x))))[:N]
    voice, fx = np.zeros(N, np.float32), np.zeros(N, np.float32)
    for slug, shot, rel in cfg["audio"]:
        x = read_wav(ROOT / "audio" / f"{slug}.wav")
        i = int((S[shot] + rel) * SR)
        x = x[: N - i]
        (fx if slug.startswith("sfx") else voice)[i:i + len(x)] += x
    raw, clean = OUT / f"v{n}_raw.wav", OUT / f"v{n}_clean.wav"
    write(raw, voice / np.abs(voice).max() * 0.9)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(raw), "-af", VOICE_FX, "-ar", str(SR), "-ac", "1", str(clean)], check=True)
    v = fit(read_wav(clean))
    v = v / np.abs(v).max() * 0.9
    act = smooth(np.abs(v), 2205) > 0.008
    duck = np.clip(smooth(act.astype(np.float32), 13230) * 2, 0, 1)
    music = fit(read_wav(ROOT / "audio" / f"{cfg['music'][0]}.wav"))
    amb = fit(read_wav(ROOT / "audio" / f"{cfg['amb'][0]}.wav"))
    amb[int(S[4] * SR):] *= np.linspace(1, 0, N - int(S[4] * SR))
    music, amb = music / np.abs(music).max(), amb / np.abs(amb).max()
    bed = music * 0.035 * (1 - 0.5 * duck) + amb * 0.03 * (1 - 0.4 * duck)
    out = v + bed + fx * 0.15
    fade = int(0.8 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    mixf = OUT / f"pg{n}_remix.wav"
    write(mixf, out / np.abs(out).max() * 0.95)
    meas = subprocess.run([FF, "-i", str(mixf), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    lufs = float([l for l in meas.splitlines() if l.strip().startswith("I:")][-1].split()[1])
    gain = -14.0 - lufs
    src = ROOT / "planet_gym" / f"{cfg['name']}.mp4"
    tmp = OUT / f"{cfg['name']}_tmp.mp4"
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(src), "-i", str(mixf), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-af", f"volume={gain:.2f}dB,alimiter=limit=0.89:attack=5:release=50", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(src)
    for f in (raw, clean, mixf):
        f.unlink()
    print("REMIXED", src, flush=True)


if __name__ == "__main__":
    for n in [int(a) for a in sys.argv[1:]] or list(EPS):
        remix(n)
