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
END = ("GymBoss got you! Start your free trial.", ["got you", "free trial"])
LINES = {
    "r1a": ("P.O.V. It's the fifth, and nobody has paid their fees.", ["paid", "fees"]),
    "r1b": ("GymBoss puts every pending due in one list.", ["pending", "list"]),
    "r1c": ("Auto reminders. One-tap renewals. Payment received!", ["reminders", "renewals", "received"]),
    "r1d": ("Less chasing. More cash in the bank.", ["chasing", "cash"]),
    "r1e": END,
    "r2a": ("Twenty late payers? That's forty thousand rupees stuck, every month.", ["late", "forty thousand", "month"]),
    "r2b": ("Missed renewals. Expired members. Forgotten dues.", ["renewals", "expired", "dues"]),
    "r2c": ("GymBoss flags every expiry and every due, automatically.", ["expiry", "automatically"]),
    "r2d": ("Plus your monthly finance report, in one tap.", ["finance", "one tap"]),
    "r2e": END,
    "r3a": ("Me, at midnight, still doing gym accounts in a register.", ["midnight", "accounts", "register"]),
    "r3b": ("Cash here, U.P.I. there. Nothing adds up!", ["cash", "adds up"]),
    "r3c": ("Then I found GymBoss!", ["found"]),
    "r3d": ("Members, attendance and fees. All in one app.", ["attendance", "one app"]),
    "r3e": ("Finance PDF in one tap. Now I'm in bed by ten.", ["one tap", "bed"]),
    "r3f": END,
}


async def main(slugs):
    key = os.getenv("EMERGENT_LLM_KEY")
    tts, stt = OpenAITextToSpeech(api_key=key), OpenAISpeechToText(api_key=key)
    for slug in slugs:
        text, must = LINES[slug]
        for attempt in range(4):
            audio = await tts.generate_speech(text=text, model="tts-1-hd", voice="ash", speed=1.1, response_format="wav")
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
