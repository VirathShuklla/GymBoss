from pathlib import Path
from PIL import Image
from rembg import new_session, remove

SRC = Path(__file__).parent / "assets"
OUT = SRC / "cut"
OUT.mkdir(exist_ok=True)
session = new_session("isnet-anime")

for f in sorted(SRC.glob("panda_*.jpg")):
    img = remove(Image.open(f).convert("RGB"), session=session, post_process_mask=True)
    a = img.getchannel("A").point(lambda v: 0 if v < 40 else v)
    img.putalpha(a)
    img = img.crop(img.getbbox())
    img.save(OUT / (f.stem + ".png"))
    print(f.stem, img.size)

prev = Image.new("RGB", (1600, 420), (40, 16, 80))
for i, p in enumerate(sorted(OUT.glob("*.png"))):
    im = Image.open(p)
    im.thumbnail((200, 400))
    prev.paste(im, (i * 200, 10), im)
prev.save(SRC / "preview.png")
