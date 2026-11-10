import numpy as np
from music import SR, add, env, hz, lp, noise, save, tone, OUT

rng = np.random.default_rng(5)


def pad_bar(mix, t0, dur, ch, g, cut=0.06):
    pad = sum(tone(hz(m), dur + 0.6, 5, 0.003) for m in ch)
    pad *= np.minimum(1, np.arange(len(pad)) / (0.8 * SR)) * np.minimum(1, (len(pad) - np.arange(len(pad))) / (0.6 * SR))
    add(mix, lp(pad, cut), t0, g)


def plucks(mix, t0, notes, step, g, dec=0.12, harm=3):
    for s, m in enumerate(notes):
        n = int(0.6 * SR)
        add(mix, tone(hz(m), 0.6, harm)[:n] * env(n, 0.001, dec), t0 + s * step, g)


def savanna(dur):
    beat, mix = 60 / 72, np.zeros(int(dur * SR))
    prog = [[53, 57, 60, 64], [55, 59, 62, 67], [57, 60, 64, 69], [55, 59, 62, 66]]
    for bar in range(int(dur / (4 * beat)) + 1):
        t0, ch = bar * 4 * beat, prog[bar % 4]
        pad_bar(mix, t0, 4 * beat, ch, 0.12)
        add(mix, tone(hz(ch[0] - 24), 4 * beat, 2) * env(int(4 * beat * SR), 0.02, 1.5), t0, 0.25)
        plucks(mix, t0, [ch[0] + 12, ch[2] + 12, ch[1] + 12, ch[3] + 12, ch[2] + 12, ch[1] + 24], beat * 2 / 3, 0.09)
        if bar % 2:
            for k in range(4):
                n = int(0.12 * SR)
                add(mix, lp(noise(0.12), 0.4) * env(n, 0.001, 0.03), t0 + k * beat + beat / 2, 0.05)
    return mix


def arctic(dur):
    beat, mix = 60 / 66, np.zeros(int(dur * SR))
    prog = [[62, 66, 69, 73], [59, 62, 66, 69], [55, 59, 62, 66], [57, 61, 64, 69]]
    for bar in range(int(dur / (4 * beat)) + 1):
        t0, ch = bar * 4 * beat, prog[bar % 4]
        pad_bar(mix, t0, 4 * beat, ch, 0.1, 0.08)
        for s, m in enumerate([ch[3] + 12, ch[1] + 24, ch[2] + 12, ch[0] + 24]):
            n = int(1.2 * SR)
            bell = (tone(hz(m), 1.2, 1) + 0.4 * tone(hz(m) * 2.76, 1.2, 1))[:n] * env(n, 0.001, 0.5)
            add(mix, bell, t0 + s * beat, 0.05)
    return mix


def spooky(dur):
    beat, mix = 60 / 60, np.zeros(int(dur * SR))
    prog = [[50, 53, 57, 60], [46, 50, 53, 57], [48, 51, 55, 58], [49, 52, 55, 58]]
    for bar in range(int(dur / (4 * beat)) + 1):
        t0, ch = bar * 4 * beat, prog[bar % 4]
        pad_bar(mix, t0, 4 * beat, ch, 0.12, 0.05)
        plucks(mix, t0, [ch[0] + 24, ch[2] + 12, ch[3] + 12, ch[1] + 24], beat, 0.06, 0.3, 2)
    t = np.arange(len(mix)) / SR
    mel = np.array([74, 72, 69, 70, 72, 69, 67, 69], float)
    f = hz(mel[(t / 2).astype(int) % 8]) * (1 + 0.012 * np.sin(2 * np.pi * 5.5 * t))
    mix += np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.035 * (0.5 + 0.5 * np.sin(np.pi * (t % 2) / 2))
    return mix


def tropical(dur):
    beat, mix = 60 / 104, np.zeros(int(dur * SR))
    prog = [[60, 64, 67], [65, 69, 72], [67, 71, 74], [65, 69, 72]]
    for bar in range(int(dur / (4 * beat)) + 1):
        t0, ch = bar * 4 * beat, prog[bar % 4]
        pad_bar(mix, t0, 4 * beat, ch, 0.05, 0.1)
        for b in range(4):
            n = int(0.3 * SR)
            add(mix, tone(hz(ch[0] - 24), 0.3, 3)[:n] * env(n, 0.003, 0.12), t0 + b * beat, 0.3)
            add(mix, lp(noise(0.08), 0.6) * env(int(0.08 * SR), 0.001, 0.02), t0 + b * beat + beat / 2, 0.08)
        pat = [0, 2, 1, 2, 0, 1, 2, 1]
        plucks(mix, t0, [ch[i] + 12 for i in pat], beat / 2, 0.12, 0.09, 4)
    return mix


def amb_savanna(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = lp(noise(dur), 0.03) * 0.25 * (0.7 + 0.3 * np.sin(t * 0.7))
    cic = np.sin(2 * np.pi * 4200 * t) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 38 * t))) * (0.5 + 0.5 * np.sin(t * 1.3)) * 0.04
    for at in np.arange(0.5, dur, 2.3):
        bn = int(0.18 * SR)
        bt = np.arange(bn) / SR
        add(out, np.sin(2 * np.pi * np.cumsum(2600 + 900 * np.sin(bt * 60)) / SR) * env(bn, 0.01, 0.06), at + rng.uniform(0, 0.8), 0.06)
    return out + cic


def amb_arctic(dur):
    t = np.arange(int(dur * SR)) / SR
    return lp(noise(dur), 0.015) * (0.6 + 0.4 * np.sin(t * 0.9) * np.sin(t * 0.37)) * 0.9


def amb_forest(dur):
    t = np.arange(int(dur * SR)) / SR
    out = lp(noise(dur), 0.01) * 0.4
    out += np.sin(2 * np.pi * 4800 * t) * (np.sin(2 * np.pi * 3 * t) > 0.6) * (np.sin(2 * np.pi * 60 * t) > 0) * 0.03
    for at in np.arange(1.5, dur, 6):
        for k in range(2):
            on = int(0.35 * SR)
            add(out, tone(420 - k * 40, 0.35, 2)[:on] * env(on, 0.05, 0.15), at + k * 0.45, 0.05)
    return out


def amb_jungle(dur):
    out = lp(noise(dur), 0.25) * 0.12 + lp(noise(dur), 0.05) * 0.2
    for at in np.arange(0.3, dur, 1.1):
        bn = int(0.12 * SR)
        bt = np.arange(bn) / SR
        f0 = rng.uniform(1800, 3600)
        add(out, np.sin(2 * np.pi * np.cumsum(f0 + 1200 * bt / 0.12) / SR) * env(bn, 0.005, 0.04), at + rng.uniform(0, 0.5), 0.05)
    return out


if __name__ == "__main__":
    D = 26
    for name, fn in [("pg_music_1", savanna), ("pg_music_2", arctic), ("pg_music_3", spooky), ("pg_music_4", tropical),
                     ("pg_amb_1", amb_savanna), ("pg_amb_2", amb_arctic), ("pg_amb_3", amb_forest), ("pg_amb_4", amb_jungle)]:
        save(name, fn(D))
        print(name, flush=True)
