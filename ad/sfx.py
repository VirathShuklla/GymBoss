import wave
from pathlib import Path
import numpy as np

SR = 24000
OUT = Path(__file__).parent / "audio"
rng = np.random.default_rng(3)
t = lambda d: np.arange(int(d * SR)) / SR


def save(name, x, gain):
    x = x / (np.abs(x).max() + 1e-9) * gain
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


a = t(0.12)
save("sfx_pop", np.sin(2 * np.pi * np.cumsum(700 + 900 * a / 0.12) / SR) * np.exp(-a * 35), 0.35)

a = t(0.9)
bell = sum(np.sin(2 * np.pi * f * a) / (k + 1) for k, f in enumerate([1568, 2093, 3136]))
hit = rng.uniform(-1, 1, len(a)) * np.exp(-a * 60)
save("sfx_ching", bell * np.exp(-a * 5) + hit * 0.6, 0.45)

a = t(0.8)
boom = np.sin(2 * np.pi * np.cumsum(45 + 90 * np.exp(-a * 12)) / SR) * np.exp(-a * 4)
save("sfx_boom", boom + rng.uniform(-1, 1, len(a)) * np.exp(-a * 40) * 0.3, 0.8)

a = t(0.35)
noise = rng.uniform(-1, 1, len(a))
sweep = np.sin(2 * np.pi * np.cumsum(300 + 1200 * np.abs(np.sin(a * 18))) / SR)
save("sfx_scratch", (noise * 0.5 + sweep) * np.exp(-a * 6), 0.4)
print("sfx ok")
