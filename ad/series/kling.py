import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
KEY = os.environ["EMERGENT_LLM_KEY"]
# Fal Universal Key supports queue inference through Emergent proxy, not Platform APIs.
CONTROL = os.environ.get("INTEGRATION_PROXY_URL", "https://integrations.emergentagent.com").rstrip("/") + "/api/v1/fal"
ENDPOINT = "fal-ai/kling-video/v3/standard/image-to-video"
IMG = "https://static.prod-images.emergentagent.com/jobs/a02a4ec5-b273-45c4-aa83-d9a1e3a0b574/images/"
OUT = Path(__file__).parent / "clips"
OUT.mkdir(exist_ok=True)
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
STYLE = " 3D cartoon animation, expressive comedic acting, smooth character animation, stable camera, the panda keeps the same design: purple headband, black sunglasses, black hoodie."

SHOTS = {
    "a1": ("489f7bdae6605c11db0d1328845b23d25549ab688b3d4051b590f874c7c5fc5a", "The panda stares at the phone, reads a message, slowly turns his head to look straight at the camera with a deadpan unimpressed face, exaggerated slow sigh, shoulders drop."),
    "a2": ("fd98144acfa7ed7bf56200bb18ec32cd05139497d1d47d8c5e29f853ce9624a0", "Dramatic slow push-in on the panda's face as he slowly lowers his sunglasses down his nose revealing intense sarcastic eyes, one eyebrow rises, neon lights flicker, soap-opera dramatic moment."),
    "a3": ("d630fb40e4b1abec21118ab7e31352740390c353a0a79edc2a0b90d091e733c0", "The panda sips the protein shake loudly, the phone on the desk lights up green, he glances at it, grins smugly, and gives a lazy chef's kiss gesture while rocking back in the chair."),
    "b1": ("17ca213aa8dfd0d1ac2c54d5ce17b339e36fac365686a23814a451984ba762e8", "Film noir: the detective panda slowly moves the magnifying glass across the register page, squints suspiciously, rain runs down the window, lamp light flickers, smoke drifts."),
    "b2": ("be75cdc032efe372f2b1f67700f408a2a5d4b8acbcd5297442df838c959bf437", "The panda frantically jabs at the conspiracy board, pulling a red string between receipts, turning to the camera with wild unhinged eyes, then pointing back at the board, manic energy."),
    "b3": ("384d7fb52fddf2956d04128689e70a3b89058a9e78b56e7a46544ced43b68d8c", "The panda reads the paper, eyes widen in horror, he slowly lowers the paper, stares blankly at the camera in shame, then dramatically facepalms with one paw."),
    "c1": ("0b391ba0606da559a0e92a43dc900244b650b615ad7e4f52fe6d94bf21eb5ad0", "Wildlife documentary: the panda tiptoes sneakily through the tall golden grass, crouching low, peeking over the grass, grass sways in the breeze, handheld telephoto camera feel."),
    "c2": ("53c266c4db9c0bf644d7164937555e75b0ad3dd3d65d2ee720ec2dede68f7870", "The panda sprints after the fleeing gym member across the savanna waving the long receipt, comedic cartoon running, dust clouds, the member runs away faster, camera tracking."),
    "c3": ("38258d711a89dac9a98dfecc62c9686b21f2e5c25b4fc41a58b3a33f5b425ddb", "The panda swings gently in the hammock, the phone screen glows green, he smiles blissfully, kicks one leg happily and sips the coconut drink, palm leaves sway at sunset."),
}


def run(slug):
    img, prompt = SHOTS[slug]
    dst = OUT / f"{slug}.mp4"
    if dst.exists():
        return slug, "cached"
    payload = {"start_image_url": IMG + img + ".jpeg", "prompt": prompt + STYLE, "duration": "5", "generate_audio": False,
               "negative_prompt": "blur, distort, low quality, extra limbs, text, watermark, morphing face"}
    r = requests.post(f"{CONTROL}/proxy", headers={**H, "X-Fal-Target-Url": f"https://queue.fal.run/{ENDPOINT}"}, json=payload, timeout=60)
    if r.status_code == 402:
        return slug, "INSUFFICIENT CREDITS"
    r.raise_for_status()
    sub = r.json()
    deadline = time.time() + 1500
    while time.time() < deadline:
        try:
            st = requests.get(sub["status_url"], headers=H, timeout=30).json()
        except requests.RequestException:
            time.sleep(5)
            continue
        s = (st.get("status") or "").upper()
        if s in {"COMPLETED", "OK"}:
            res = requests.get(sub["response_url"], headers=H, timeout=60).json()
            url = res["video"]["url"]
            dst.write_bytes(requests.get(url, timeout=120).content)
            return slug, "ok"
        if s in {"FAILED", "CANCELLED", "CANCELED", "ERROR"}:
            return slug, f"failed {json.dumps(st)[:300]}"
        time.sleep(8)
    return slug, "timeout"


if __name__ == "__main__":
    slugs = sys.argv[1:] or list(SHOTS)
    with ThreadPoolExecutor(len(slugs)) as ex:
        for slug, res in ex.map(run, slugs):
            print(slug, res, flush=True)
