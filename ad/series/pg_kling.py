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
MODELS = {"v3pro": "fal-ai/kling-video/v3/pro/image-to-video", "v26pro": "fal-ai/kling-video/v2.6/pro/image-to-video"}
IMG = "https://static.prod-images.emergentagent.com/jobs/a02a4ec5-b273-45c4-aa83-d9a1e3a0b574/images/"
OUT = Path(__file__).parent / "pg_clips"
OUT.mkdir(exist_ok=True)
H = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
STYLE = " High-end 3D cartoon animation like a Pixar film, expressive comedic acting, fluid natural motion, cinematic, the panda keeps exactly the same design and face: purple headband with white dumbbell, black sunglasses, black hoodie. No text."
NEG = "blur, distort, low quality, extra limbs, extra fingers, morphing, face changing, flicker, text, watermark, subtitles"

SHOTS = {
    "e1_1": ("0b391ba0606da559a0e92a43dc900244b650b615ad7e4f52fe6d94bf21eb5ad0", "Wildlife documentary telephoto shot: the panda tiptoes sneakily through the tall golden grass, crouching low, slowly peeking over the grass with narrowed eyes, the grass sways in a warm breeze, slow gentle camera push-in."),
    "e1_2": ("53c266c4db9c0bf644d7164937555e75b0ad3dd3d65d2ee720ec2dede68f7870", "The panda sprints after the fleeing gym member across the savanna waving the long receipt over his head, bouncy cartoon running, dust clouds kick up, the member runs away even faster, camera tracks alongside."),
    "e1_3": ("35733f5e27a64c4f751202859a2b61c6e717291bd3d90ec2a0d3d0f8fd9e2ef7", "Static camera. The back of the hoodie stays plain black. The exhausted panda lies face-down in the dust, slowly lifts one trembling paw in defeat and lets it flop back down, tongue out, the receipt flutters in the wind, dust settles, the tiny member disappears over the horizon."),
    "e1_4": ("38258d711a89dac9a98dfecc62c9686b21f2e5c25b4fc41a58b3a33f5b425ddb", "The panda swings gently in the hammock, his phone screen glows green, he smiles blissfully, kicks one leg happily and sips the coconut drink, palm leaves sway in the sunset breeze."),
    "e2_1": ("b68154b8a0fc36dbe21f9395969fd09cf9f1094cede867d1b7443410fc91cc90", "The panda lies on the snowy ridge watching through binoculars, then slowly lowers them with a dramatic gasp of excitement, snow falls gently, the aurora ripples across the sky, slow camera push-in."),
    "e2_2": ("01555c4b0329b135294f6ebc7bd52175a5dbc505456f058adf7ff5a6c47558f1", "The huge herd of new-year gym people stampedes through the snow into the glowing gym cabin, snow spraying everywhere, while the panda beside the door spins around in joy throwing his clipboard up in the air."),
    "e2_3": ("06e9dc140b54e3bd46bd514127f447c3d6714afe87916794606ea9271d614d9a", "In the empty cold gym the lonely panda sighs heavily, a small snow tumbleweed rolls slowly past his feet, he slowly turns his head to watch it go, deadpan sadness, snowflakes drift by the window."),
    "e2_4": ("8f48c04c4c1a208b2b1721dcb39e182fe65efbd330908b3e58c96ddbe7fca006", "Static camera, no zoom. By the crackling fireplace the panda keeps his black sunglasses on the whole time, sips hot cocoa, draws a big red circle on the calendar with the marker, then grins mischievously and rubs his paws together. The panda stays seated in the armchair."),
    "e3_1": ("f6c5973d3e003575d14f4be7daeb4d4a933da05139b91f5e48a31b623519cede", "The nervous panda tiptoes forward through the misty moonlit forest holding the glowing lantern high, looking left and right, fireflies drift, fog rolls along the ground, slow camera follow."),
    "e3_2": ("5feddfc1ef137b458023df9ff745927449b6edd758b045a86544a604a246051b", "The translucent ghost gym member floats out from behind the tree waving spookily, the panda jumps high in fright with arms flailing and the lantern swinging, hilarious scared cartoon reaction, fireflies scatter."),
    "e3_3": ("471d2be3b0b9ab64805b3a2bcabd9fa4fc14e3908bdc6b33af85ea17fc9c3f91", "The panda chases the floating ghost member through the moonlit clearing, waving the long paper invoice, the ghost glides away giggling and waves bye-bye, leaves swirl, camera tracks the chase."),
    "e3_4": ("d8c0147c255410da7c127ec23c0eadca6addd1ba6ee6fcb224a69b472dd31792", "Static camera. Sitting on the mossy log, the panda looks at his glowing green phone and nods smugly, the cute ghost member taps its own glowing ghost phone and gives a happy thumbs up, fireflies sparkle. The white GYMBOSS logo on the panda's hoodie stays sharp and unchanged."),
    "e4_1": ("303d70da8b36e49a312c51bc128324779f32bb7c06a53b2a4575a812c642932e", "Hidden behind the giant leaves, the panda slowly raises his binoculars and watches the muscular gym bro chugging the giant shaker by the chocolate shake waterfall, leaves rustle, the waterfall flows, slow push-in."),
    "e4_2": ("8ddc90fc6e2eed3b5cbe2a6deaf2c0b40655f86f320deda1842bd42d9d066fab", "The gym bro performs a wild ritual dance violently shaking the giant shaker above his head with powder puffs flying, and the panda beside him copies the dance awkwardly with a tiny shaker, comedic rhythm, sparkles."),
    "e4_3": ("3384fa47abae9d70eea5c11339c01c45fc083344efebaeb7aa85076e1a8ebbcd", "Static medium shot, camera does not move or zoom. The panda takes a long sip through the straw, his cheeks puff up and his eyes grow enormous with shock, the sunglasses stay resting on top of his purple headband, then he lowers the shaker slightly and a huge delighted grin spreads across his face. The purple headband stays on his head the whole time."),
    "e4_4": ("37d3d69f91e0406efe92ad87c0847eef122ddcc97609d253e1b9f8f00745664c", "The addicted panda stands under the chocolate shake waterfall with mouth wide open gulping it directly, shaking both shakers happily, splashes everywhere, while the gym bro in the background slowly facepalms."),
}


def run(job):
    slug, model = job
    img, prompt = SHOTS[slug]
    dst = OUT / f"{slug}_{model}.mp4"
    if dst.exists():
        return slug, model, "cached"
    payload = {"start_image_url": IMG + img + ".jpeg", "prompt": prompt + STYLE, "duration": "5", "generate_audio": False, "negative_prompt": NEG}
    r = requests.post(f"{CONTROL}/proxy", headers={**H, "X-Fal-Target-Url": f"https://queue.fal.run/{MODELS[model]}"}, json=payload, timeout=60)
    if r.status_code == 402:
        return slug, model, "INSUFFICIENT CREDITS"
    if not r.ok:
        return slug, model, f"submit {r.status_code} {r.text[:200]}"
    sub = r.json()
    deadline = time.time() + 1800
    while time.time() < deadline:
        try:
            st = requests.get(sub["status_url"], headers=H, timeout=30).json()
        except requests.RequestException:
            time.sleep(5)
            continue
        s = (st.get("status") or "").upper()
        if s in {"COMPLETED", "OK"}:
            for _ in range(5):
                try:
                    res = requests.get(sub["response_url"], headers=H, timeout=60).json()
                    dst.write_bytes(requests.get(res["video"]["url"], timeout=180).content)
                    return slug, model, "ok"
                except (requests.RequestException, KeyError):
                    time.sleep(5)
            return slug, model, "download failed"
        if s in {"FAILED", "CANCELLED", "CANCELED", "ERROR"}:
            return slug, model, f"failed {json.dumps(st)[:300]}"
        time.sleep(8)
    return slug, model, "timeout"


if __name__ == "__main__":
    model = sys.argv[1]
    slugs = sys.argv[2:] or list(SHOTS)
    with ThreadPoolExecutor(len(slugs)) as ex:
        for res in ex.map(run, [(s, model) for s in slugs]):
            print(*res, flush=True)
