import asyncio
import json
import os
import subprocess
from pathlib import Path

import imageio_ffmpeg
from dotenv import load_dotenv
from emergentintegrations.llm.openai import OpenAISpeechToText, OpenAITextToSpeech

from steps import CHAPTERS

load_dotenv("/app/backend/.env")
F = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = Path(__file__).parent
OUT = ROOT / "vo"
OUT.mkdir(exist_ok=True)


async def one(tts, stt, s, sem, durs):
    async with sem:
        path = OUT / f"{s['id']}.wav"
        if not path.exists():
            audio = await tts.generate_speech(text=s["vo"], model="tts-1-hd", voice="nova", speed=0.97, response_format="wav")
            path.write_bytes(audio)
        durs[s["id"]] = round((path.stat().st_size - 44) / 48000, 2)
        subprocess.run([F, "-y", "-loglevel", "error", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", str(path), f"/tmp/{s['id']}.mp3"], check=True)
        with open(f"/tmp/{s['id']}.mp3", "rb") as fh:
            heard = (await stt.transcribe(file=fh, model="whisper-1", response_format="text")).text.lower()
        words = [w for w in s["vo"].lower().replace(",", "").replace(".", "").split() if len(w) > 5]
        miss = [w for w in words if w.strip("'!?") not in heard]
        print(s["id"], durs[s["id"]], "MISS" if len(miss) > 2 else "OK", miss[:4], flush=True)


async def main():
    key = os.getenv("EMERGENT_LLM_KEY")
    tts, stt = OpenAITextToSpeech(api_key=key), OpenAISpeechToText(api_key=key)
    durs, sem = {}, asyncio.Semaphore(6)
    await asyncio.gather(*[one(tts, stt, s, sem, durs) for ch in CHAPTERS for s in ch["steps"]])
    (ROOT / "vo_durs.json").write_text(json.dumps(durs, indent=1))
    print("TOTAL", round(sum(durs.values()), 1))

asyncio.run(main())
