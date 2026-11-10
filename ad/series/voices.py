import asyncio
import os
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from dotenv import load_dotenv
from emergentintegrations.llm.openai import OpenAISpeechToText, OpenAITextToSpeech

load_dotenv("/app/backend/.env")
F = imageio_ffmpeg.get_ffmpeg_exe()
OUT = Path(__file__).parent / "audio"
OUT.mkdir(exist_ok=True)
PANDA, NARR = ("onyx", 0.95), ("fable", 0.92)
LINES = {
    "a_1": (PANDA, "Tomorrow. He said... tomorrow.", ["tomorrow"]),
    "a_2": (PANDA, "That was six tomorrows ago.", ["six", "ago"]),
    "a_3": (PANDA, "So I let the app ask. Paid in ten minutes. I love technology.", ["app", "paid", "technology"]),
    "a_4": (PANDA, "You're welcome.", ["welcome"]),
    "c_1": (NARR, "Here, we observe the wild gym owner... silently stalking his prey.", ["gym owner", "prey"]),
    "c_2": (NARR, "The member who forgot to renew. Again. A tragic chase.", ["renew", "tragic"]),
    "c_3": (NARR, "But this one has evolved. He uses GymBoss... and renewals simply arrive.", ["evolved", "renewals"]),
    "c_4": (NARR, "Start your free trial.", ["free trial"]),
}


async def main(slugs):
    key = os.getenv("EMERGENT_LLM_KEY")
    tts, stt = OpenAITextToSpeech(api_key=key), OpenAISpeechToText(api_key=key)
    for slug in slugs:
        (voice, speed), text, must = LINES[slug]
        for attempt in range(3):
            audio = await tts.generate_speech(text=text, model="tts-1-hd", voice=voice, speed=speed, response_format="wav")
            path = OUT / f"{slug}.wav"
            path.write_bytes(audio)
            subprocess.run([F, "-y", "-loglevel", "error", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", str(path), f"/tmp/{slug}.mp3"], check=True)
            with open(f"/tmp/{slug}.mp3", "rb") as fh:
                heard = (await stt.transcribe(file=fh, model="whisper-1", response_format="text")).text.lower()
            ok = all(m in heard for m in must)
            print(slug, attempt, round((len(audio) - 44) / 48000, 2), heard, "OK" if ok else "RETRY", flush=True)
            if ok:
                break

asyncio.run(main(sys.argv[1:] or list(LINES)))
