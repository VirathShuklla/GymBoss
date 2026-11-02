import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from emergentintegrations.llm.openai import OpenAITextToSpeech

load_dotenv("/app/backend/.env")
OUT = Path(__file__).parent / "audio"
OUT.mkdir(exist_ok=True)

SCRIPTS = {
    "wide": [
        ("w1", "Meet GymBoss. The panda who runs your gym, so you don't have to."),
        ("w2", "Add members in seconds. Photos, plans, all in one place."),
        ("w3", "Fees and dues? Tracked. Payment received!"),
        ("w4", "Attendance, renewals and expiry reminders. Sorted."),
        ("w5", "Finance reports and a monthly PDF in one tap."),
        ("w6", "Multiple outlets, staff access, on web and mobile."),
        ("w7", "No excuses, bro! Manage. Grow. Repeat."),
        ("w8", "GymBoss got you! Start your free trial."),
    ],
    "vertical": [
        ("v1", "Gym owners! Meet GymBoss."),
        ("v2", "Members, fees and dues, all tracked."),
        ("v3", "Attendance and renewals, sorted."),
        ("v4", "Reports and a monthly PDF, one tap."),
        ("v5", "No excuses, bro! Manage. Grow. Repeat."),
        ("v6", "GymBoss got you! Start your free trial."),
    ],
}


async def main():
    tts = OpenAITextToSpeech(api_key=os.getenv("EMERGENT_LLM_KEY"))
    for lines in SCRIPTS.values():
        for slug, text in lines:
            audio = await tts.generate_speech(text=text, model="tts-1-hd", voice="ash", speed=1.08, response_format="wav")
            (OUT / f"{slug}.wav").write_bytes(audio)
            print(slug, len(audio))

asyncio.run(main())
