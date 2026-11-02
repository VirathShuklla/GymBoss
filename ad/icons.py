import json
import re
from pathlib import Path

SRC = Path("/app/frontend/node_modules/lucide-react/dist/esm/icons")
NAMES = ["users", "user-plus", "indian-rupee", "circle-check", "qr-code", "calendar-clock", "bell-ring",
         "chart-column", "file-text", "building-2", "shield-check", "smartphone", "monitor", "crown",
         "fingerprint", "trending-up", "camera", "refresh-cw", "search", "wallet", "dumbbell"]
out = {}
for n in NAMES:
    src = (SRC / f"{n}.js").read_text()
    body = src.split("__iconNode = [", 1)[1].split("];", 1)[0]
    parts = []
    for tag, attrs in re.findall(r'\[\s*"(\w+)",\s*\{([^}]*)\}\s*\]', body):
        kv = re.findall(r'(\w+): "([^"]*)"', attrs)
        parts.append(f"<{tag} " + " ".join(f'{k}="{v}"' for k, v in kv if k != "key") + "/>")
    out[n] = "".join(parts)
    assert parts, n
Path(__file__).with_name("icons.js").write_text("window.ICONS=" + json.dumps(out) + ";")
print(len(out))
