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
LINES = {
    "v1": ("Hey, gym owners! Meet GymBoss.", ["owners", "meet"]),
    "v4": ("Finance reports, and a monthly PDF in one tap.", ["reports", "pdf"]),
    "v5": ("No excuses, bro! Manage. Grow. Repeat.", ["excuses", "grow", "repeat"]),
}


async def main(slugs):
    key = os.getenv("EMERGENT_LLM_KEY")
    tts, stt = OpenAITextToSpeech(api_key=key), OpenAISpeechToText(api_key=key)
    for slug in slugs:
        text, must = LINES[slug]
        for attempt in range(4):
            audio = await tts.generate_speech(text=text, model="tts-1-hd", voice="ash", speed=1.0, response_format="wav")
            path = OUT / f"{slug}.wav"
            path.write_bytes(audio)
            subprocess.run([F, "-y", "-loglevel", "error", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", str(path), f"/tmp/{slug}.mp3"], check=True)
            with open(f"/tmp/{slug}.mp3", "rb") as fh:
                heard = (await stt.transcribe(file=fh, model="whisper-1", response_format="text")).text.lower()
            ok = all(m in heard for m in must)
            print(slug, attempt, round((len(audio) - 44) / 48000, 2), heard, "OK" if ok else "RETRY", flush=True)
            if ok:
                break

asyncio.run(main(sys.argv[1:]))
