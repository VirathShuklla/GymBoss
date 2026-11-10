import sys
import wave
from pathlib import Path

import numpy as np

SR = 44100
OUT = Path(__file__).parent / "audio"
rng = np.random.default_rng(11)
hz = lambda m: 440 * 2 ** ((m - 69) / 12)


def env(n, a=0.002, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)


def tone(f, dur, harm=1, detune=0.0):
    t = np.arange(int(dur * SR)) / SR
    out = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, harm + 1))
    if detune:
        out = out + sum(np.sin(2 * np.pi * f * (1 + detune) * k * t) / k for k in range(1, harm + 1))
    return out


def lp(x, a):
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc)
        y[i] = acc
    return y


def add(buf, sig, at, g=1.0):
    i = int(at * SR)
    if i >= len(buf):
        return
    sig = sig[: len(buf) - i]
    buf[i:i + len(sig)] += sig * g


def noise(dur):
    return rng.uniform(-1, 1, int(dur * SR))


def kick():
    n = int(0.4 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(48 + 120 * np.exp(-t * 28)) / SR) * env(n, 0.001, 0.16)


def synthwave(dur):
    beat = 60 / 108
    mix = np.zeros(int(dur * SR))
    prog = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [55, 60, 64]), (55, [55, 59, 62])]
    for bar in range(int(dur / (4 * beat)) + 1):
        t0 = bar * 4 * beat
        root, ch = prog[bar % 4]
        for b in range(4):
            add(mix, kick(), t0 + b * beat, 0.9)
            if b in (1, 3):
                sn = np.diff(noise(0.35), prepend=0) * env(int(0.35 * SR), 0.001, 0.12)
                sn[int(0.2 * SR):] = 0
                add(mix, sn, t0 + b * beat, 0.35)
            for e in range(2):
                bn = int(beat / 2 * SR)
                add(mix, tone(hz(root - 24), beat / 2, 6)[:bn] * env(bn, 0.004, 0.14), t0 + (b + e / 2) * beat, 0.3)
        for s in range(16):
            an = int(beat / 4 * SR)
            m = ch[s % 3] + 12 + (12 if s % 8 >= 6 else 0)
            add(mix, tone(hz(m), beat / 4, 5)[:an] * env(an, 0.002, 0.07), t0 + s * beat / 4, 0.07)
        pad = sum(tone(hz(m), 4 * beat, 6, 0.004) for m in ch)
        add(mix, pad * np.minimum(1, np.arange(len(pad)) / (0.4 * SR)), t0, 0.025)
    return lp(mix, 0.3) * 0.5 + mix * 0.5


def noir(dur):
    beat = 60 / 84
    mix = np.zeros(int(dur * SR))
    walk = [45, 48, 50, 52, 53, 52, 50, 48, 41, 45, 48, 47, 46, 45, 44, 43]
    chords = [[57, 60, 64, 67], [53, 57, 60, 64], [52, 56, 59, 62], [57, 60, 63, 66]]
    for i, m in enumerate(walk * 4):
        t = i * beat
        if t > dur:
            break
        n = int(beat * SR)
        add(mix, tone(hz(m - 12), beat, 4)[:n] * env(n, 0.005, 0.25), t, 0.45)
        sw = noise(beat * 0.6) * np.linspace(0, 1, int(beat * 0.6 * SR)) ** 2 * np.exp(-np.arange(int(beat * 0.6 * SR)) / SR / 0.05)
        if i % 2:
            add(mix, lp(sw, 0.5), t, 0.18)
        ride = np.diff(noise(0.3), prepend=0) * env(int(0.3 * SR), 0.001, 0.09)
        add(mix, ride, t, 0.05)
        add(mix, ride, t + beat * 0.66, 0.035)
        if i % 4 == 0:
            ch = chords[(i // 4) % 4]
            pn = int(beat * 3 * SR)
            add(mix, sum(tone(hz(c), beat * 3, 3) for c in ch)[:pn] * env(pn, 0.003, 0.6), t + beat * 0.5, 0.06)
    strings = sum(tone(hz(m), dur, 5, 0.003) for m in [45, 52, 57])
    mix += lp(strings, 0.05) * 0.06 * np.minimum(1, np.arange(len(mix)) / (2 * SR))
    return mix


def documentary(dur):
    beat = 60 / 72
    mix = np.zeros(int(dur * SR))
    prog = [[53, 57, 60, 64], [55, 59, 62, 67], [57, 60, 64, 69], [55, 59, 62, 66]]
    for bar in range(int(dur / (4 * beat)) + 1):
        t0 = bar * 4 * beat
        ch = prog[bar % 4]
        pad = sum(tone(hz(m), 4 * beat + 0.6, 5, 0.003) for m in ch)
        pad *= np.minimum(1, np.arange(len(pad)) / (0.8 * SR)) * np.minimum(1, (len(pad) - np.arange(len(pad))) / (0.6 * SR))
        add(mix, lp(pad, 0.06), t0, 0.12)
        add(mix, tone(hz(ch[0] - 24), 4 * beat, 2) * env(int(4 * beat * SR), 0.02, 1.5), t0, 0.25)
        for s, m in enumerate([ch[0] + 12, ch[2] + 12, ch[1] + 12, ch[3] + 12, ch[2] + 12, ch[1] + 24]):
            pn = int(0.5 * SR)
            add(mix, tone(hz(m), 0.5, 3)[:pn] * env(pn, 0.001, 0.12), t0 + s * beat * 2 / 3, 0.09)
    return mix


def save(name, x):
    fade = int(1.2 * SR)
    x[-fade:] *= np.linspace(1, 0, fade)
    x = x / (np.abs(x).max() + 1e-9) * 0.8
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def sfx():
    t = lambda d: np.arange(int(d * SR)) / SR
    a = t(2.5)
    thunder = lp(noise(2.5), 0.02) * (np.exp(-a * 1.6) * (1 + 0.6 * np.sin(a * 9)))
    save_raw("sfx_thunder", thunder, 0.9)
    a = t(2.2)
    sting = np.zeros(len(a))
    for at, m in [(0, 45), (0.32, 46), (0.64, 44)]:
        seg = tone(hz(m - 12), 2.2 - at, 6, 0.004) + tone(hz(m), 2.2 - at, 4)
        sting[int(at * SR):] += seg[: len(a) - int(at * SR)] * np.exp(-np.arange(len(a) - int(at * SR)) / SR / (0.25 if at < 0.6 else 1.0))
    save_raw("sfx_dundun", lp(sting, 0.15), 0.85)
    a = t(0.9)
    boom = np.sin(2 * np.pi * np.cumsum(40 + 110 * np.exp(-a * 10)) / SR) * np.exp(-a * 3.5)
    save_raw("sfx_vineboom", boom + lp(noise(0.9), 0.2) * np.exp(-a * 25) * 0.5, 0.95)
    a = t(0.6)
    save_raw("sfx_ding", sum(np.sin(2 * np.pi * f * a) / (k + 1) for k, f in enumerate([1760, 2637])) * np.exp(-a * 6), 0.5)
    a = t(0.5)
    save_raw("sfx_slurp", lp(noise(0.5), 0.25) * (0.5 + 0.5 * np.sin(a * 70)) * np.exp(-a * 3), 0.4)
    a = t(0.7)
    save_raw("sfx_whoosh", lp(noise(0.7), 0.08) * np.sin(np.pi * a / 0.7) ** 2, 0.6)


def save_raw(name, x, g):
    x = x / (np.abs(x).max() + 1e-9) * g
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    dur = float(sys.argv[1]) if len(sys.argv) > 1 else 20
    OUT.mkdir(exist_ok=True)
    save("music_a", synthwave(dur))
    save("music_b", noir(dur))
    save("music_c", documentary(dur))
    sfx()
    print("music ok")
