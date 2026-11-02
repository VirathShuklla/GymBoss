import sys
import wave
import numpy as np
from pathlib import Path

SR = 44100
BPM = 124
BEAT = 60 / BPM
rng = np.random.default_rng(7)


def env(n, a=0.002, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)


def kick():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    f = 50 + 110 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.14) * 0.9


def clap():
    n = int(0.25 * SR)
    noise = rng.uniform(-1, 1, n)
    hp = np.diff(noise, prepend=0)
    return hp * env(n, 0.002, 0.07) * 0.35


def hat(open_=False):
    n = int((0.18 if open_ else 0.05) * SR)
    hp = np.diff(rng.uniform(-1, 1, n), prepend=0)
    return hp * env(n, 0.001, 0.06 if open_ else 0.015) * 0.18


def saw(freq, n):
    t = np.arange(n) / SR
    out = sum(np.sin(2 * np.pi * freq * k * t) / k for k in range(1, 12))
    return out * 0.5


def lowpass(x, alpha):
    y = np.zeros_like(x)
    acc = 0.0
    for i in range(0, len(x)):
        acc += alpha * (x[i] - acc)
        y[i] = acc
    return y


def add(buf, sig, at):
    i = int(at * SR)
    if i >= len(buf):
        return
    sig = sig[: len(buf) - i]
    buf[i:i + len(sig)] += sig


def track(duration):
    n = int(duration * SR)
    mix = np.zeros(n)
    prog = [(45, [57, 60, 64]), (41, [57, 60, 65]), (48, [55, 60, 64]), (43, [55, 59, 62])]
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    bars = int(duration / (4 * BEAT)) + 1
    k, c, h, ho = kick(), clap(), hat(), hat(True)
    for bar in range(bars):
        t0 = bar * 4 * BEAT
        root, chord = prog[bar % 4]
        intro = bar < 1
        for b in range(4):
            tb = t0 + b * BEAT
            if not intro:
                add(mix, k, tb)
            if b in (1, 3) and not intro:
                add(mix, c, tb)
            add(mix, h, tb + BEAT / 2)
            add(mix, ho if b == 3 else h, tb + BEAT * 0.75)
            bn = int(BEAT / 2 * SR)
            for half in (0, 1):
                note = saw(hz(root - 12 + (12 if half else 0)), bn) * env(bn, 0.003, 0.12) * 0.22
                add(mix, note, tb + half * BEAT / 2)
        pn = int(4 * BEAT * SR)
        pad = sum(saw(hz(m), pn) for m in chord) * 0.05
        pad *= np.minimum(1, np.arange(pn) / (0.3 * SR)) * np.minimum(1, (pn - np.arange(pn)) / (0.3 * SR))
        add(mix, pad, t0)
        for s in range(8):
            an = int(BEAT / 2 * SR)
            m = chord[(s * 2 + bar) % 3] + 12
            add(mix, saw(hz(m), an) * env(an, 0.002, 0.08) * 0.05, t0 + s * BEAT / 2)
    mix = lowpass(mix, 0.35) * 0.6 + mix * 0.4
    fade = int(1.5 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    return mix / (np.abs(mix).max() + 1e-9) * 0.8


if __name__ == "__main__":
    dur, out = float(sys.argv[1]), Path(sys.argv[2])
    data = (track(dur) * 32767).astype(np.int16)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print("music", out, dur)
