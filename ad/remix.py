import subprocess
from pathlib import Path
from render import mix_audio, FFMPEG, ROOT

JOBS = {
    "GymBoss_Ad_16x9_30s": (30, [["w1", 0.3], ["w2", 4.2], ["w3", 7.8], ["w4", 10.6], ["w5", 14.0], ["w6", 17.3], ["w7", 21.0], ["w8", 25.6]]),
    "GymBoss_Ad_9x16_20s": (20, [["v1", 0.25], ["v2", 3.2], ["v3", 6.8], ["v4", 9.8], ["v5", 13.0], ["v6", 16.4]]),
}
for name, (total, vo) in JOBS.items():
    audio = ROOT / "out" / f"{name}.wav"
    mix_audio(total, vo, audio)
    src, tmp = ROOT / "out" / f"{name}.mp4", ROOT / "out" / f"{name}_tmp.mp4"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(src), "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(src)
    print("remixed", name)
