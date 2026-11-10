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
    "n1_1": ("Here, we observe the wild gym owner... silently stalking his prey.", ["gym owner", "prey"]),
    "n1_2": ("The member who forgot to renew. Again. A tragic chase.", ["renew", "tragic"]),
    "n1_3": ("Alas. The prey escapes... as it does every month.", ["escapes", "month"]),
    "n1_4": ("But this one has evolved. He uses GymBoss... and renewals simply arrive.", ["evolved", "renewals"]),
    "n_cta": ("Start your free trial.", ["free trial"]),
    "n_brand": ("Planet Gym. Brought to you by GymBoss.", ["planet gym", "brought to you"]),
    "n2_1": ("Every January... the great migration begins.", ["january", "migration"]),
    "n2_2": ("They arrive in thousands. New shoes. Bold promises.", ["thousands", "promises"]),
    "n2_3": ("By February... silence. Only the tumbleweed remains.", ["february", "tumbleweed"]),
    "n2_4": ("But the gym owner is patient. Only eleven months to go.", ["patient", "months"]),
    "n3_1": ("Deep in the forest lives the most elusive creature of all.", ["forest", "elusive"]),
    "n3_2": ("The ghost member. Paid once. Never seen again.", ["ghost", "never seen"]),
    "n3_3": ("The owner gives chase. But ghosts... cannot be caught.", ["chase", "caught"]),
    "n3_4": ("Unless you use GymBoss. One reminder, and even ghosts renew.", ["reminder", "ghosts renew"]),
    "n4_1": ("By the chocolate falls, we find the rare shake addict.", ["chocolate", "shake addict"]),
    "n4_2": ("His ritual is sacred. Shake. Shake. Shake again.", ["ritual", "shake again"]),
    "n4_3": ("Our owner takes his very first sip... and everything changes.", ["first sip", "everything changes"]),
    "n4_4": ("The addiction... is contagious.", ["addiction", "contagious"]),
}


async def main(slugs):
    key = os.getenv("EMERGENT_LLM_KEY")
    tts, stt = OpenAITextToSpeech(api_key=key), OpenAISpeechToText(api_key=key)
    for slug in slugs:
        text, must = LINES[slug]
        best = None
        for attempt in range(3):
            audio = await tts.generate_speech(text=text, model="tts-1-hd", voice="onyx", speed=0.92, response_format="wav")
            dur = (len(audio) - 44) / 48000
            path = OUT / f"{slug}.wav"
            path.write_bytes(audio)
            subprocess.run([F, "-y", "-loglevel", "error", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", str(path), f"/tmp/{slug}.mp3"], check=True)
            with open(f"/tmp/{slug}.mp3", "rb") as fh:
                heard = (await stt.transcribe(file=fh, model="whisper-1", response_format="text")).text.lower()
            ok = all(m in heard for m in must) and dur <= 4.55
            print(slug, attempt, round(dur, 2), heard, "OK" if ok else "RETRY", flush=True)
            if ok:
                break

asyncio.run(main(sys.argv[1:] or list(LINES)))
