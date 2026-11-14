import asyncio
import base64
import json
import re
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

URL = "https://gymboss-preview--66rae3xb.preview.emergentagent.com"
ROOT = Path(__file__).parent
FR = ROOT / "frames"
DPR = 4 / 3

CURSOR_JS = """
(() => {
  const ensure = () => {
    if (document.getElementById('tut-cur') || !document.body) return;
    const c = document.createElement('div'); c.id = 'tut-cur';
    c.innerHTML = '<svg width="30" height="30" viewBox="0 0 24 24"><path d="M4 2l15 11-6.5 1.2L16 21l-3 1.4-3.4-6.7L4 20z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    const p = JSON.parse(sessionStorage.getItem('tut-pos') || '[720,420]');
    Object.assign(c.style, {position:'fixed', left:'0', top:'0', zIndex:'2147483647', pointerEvents:'none', transform:`translate(${p[0]-4}px,${p[1]-2}px)`, filter:'drop-shadow(0 2px 4px rgba(0,0,0,.35))'});
    document.body.appendChild(c);
  };
  window.__tutMove = (x, y, ms) => { ensure(); const c = document.getElementById('tut-cur');
    c.style.transition = `transform ${ms}ms cubic-bezier(.45,.05,.25,1)`; c.style.transform = `translate(${x-4}px,${y-2}px)`;
    sessionStorage.setItem('tut-pos', JSON.stringify([x, y])); };
  window.__tutRipple = (x, y) => { const r = document.createElement('div');
    Object.assign(r.style, {position:'fixed', left:(x-22)+'px', top:(y-22)+'px', width:'44px', height:'44px', borderRadius:'50%', border:'3px solid #7C3AED', background:'rgba(124,58,237,.18)', zIndex:'2147483646', pointerEvents:'none', transition:'transform .5s ease-out, opacity .5s ease-out'});
    document.body.appendChild(r); requestAnimationFrame(() => { r.style.transform = 'scale(1.9)'; r.style.opacity = '0'; }); setTimeout(() => r.remove(), 600); };
  new MutationObserver(ensure).observe(document.documentElement, {childList: true, subtree: true});
  document.addEventListener('DOMContentLoaded', ensure);
})();
"""


class T:
    def __init__(self, page, log):
        self.page, self.log, self.t0 = page, log, None
        self.pos = (720, 420)

    def now(self):
        return time.time() - self.t0

    def ev(self, kind, **kw):
        self.log.append({"t": round(self.now(), 3), "kind": kind, **kw})

    async def box(self, sel):
        loc = self.page.locator(sel).first if isinstance(sel, str) else sel
        await loc.wait_for(state="visible", timeout=15000)
        await loc.scroll_into_view_if_needed()
        await asyncio.sleep(0.15)
        return loc, await loc.bounding_box()

    async def move(self, x, y, ms=750):
        await self.page.evaluate(f"__tutMove({x},{y},{ms})")
        self.pos = (x, y)
        await asyncio.sleep(ms / 1000 + 0.1)

    async def tap(self, sel, zoom=True, hold=0.9, pre=0.35):
        loc, b = await self.box(sel)
        x, y = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
        if zoom:
            self.ev("zoom", rect=[x - 330, y - 190, 660, 380], dur=pre + 0.75 + 0.1 + hold + 0.4)
        await self.move(x, y)
        await asyncio.sleep(pre)
        await self.page.evaluate(f"__tutRipple({x},{y})")
        self.ev("click")
        await loc.click()
        await asyncio.sleep(hold)

    async def type(self, sel, text, zoom=True, delay=0.07):
        loc, b = await self.box(sel)
        x, y = b["x"] + min(b["width"] / 2, 120), b["y"] + b["height"] / 2
        if zoom:
            self.ev("zoom", rect=[b["x"] - 120, b["y"] - 150, max(b["width"], 420) + 240, 360], dur=1.4 + len(text) * delay + 0.6)
        await self.move(x, y, 600)
        await self.page.evaluate(f"__tutRipple({x},{y})")
        self.ev("click")
        await loc.click()
        await loc.fill("")
        await loc.press_sequentially(text, delay=delay * 1000)
        await asyncio.sleep(0.6)

    async def select(self, trigger, option, zoom=True):
        await self.tap(trigger, zoom=zoom, hold=0.6)
        await self.tap(self.page.get_by_role("option", name=re.compile("^" + re.escape(option))).first, zoom=zoom, hold=0.7)

    async def focus(self, sel, sec=2.5, pad=40):
        loc, b = await self.box(sel)
        self.ev("zoom", rect=[b["x"] - pad, b["y"] - pad, b["width"] + 2 * pad, b["height"] + 2 * pad], dur=sec)
        await asyncio.sleep(sec)

    async def hold(self, sec):
        await asyncio.sleep(sec)

    async def scroll(self, dy, sec=1.2):
        await self.page.evaluate(f"window.scrollBy({{top:{dy},behavior:'instant'}})")
        await asyncio.sleep(sec)

    async def esc(self):
        await self.page.keyboard.press("Escape")
        await asyncio.sleep(0.6)


async def record(chapters, durs, only=None):
    FR.mkdir(exist_ok=True)
    for f in FR.glob("*.jpg"):
        f.unlink()
    log, frames = [], []
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1440, "height": 810}, device_scale_factor=DPR, accept_downloads=True)
        await ctx.add_init_script(CURSOR_JS)
        page = await ctx.new_page()
        t = T(page, log)

        async def on_popup(p):
            t.ev("popup", url=p.url)
            await p.close()
        ctx.on("page", lambda p: asyncio.ensure_future(on_popup(p)))
        page.on("download", lambda d: t.ev("download", name=d.suggested_filename))

        await page.goto(URL + "/login")
        await page.wait_for_timeout(2500)
        cdp = await ctx.new_cdp_session(page)

        state = {"on": True}

        async def grab():
            while state["on"]:
                try:
                    sc = (await cdp.send("Runtime.evaluate", {"expression": "[window.scrollX, window.scrollY]", "returnByValue": True}))["result"]["value"]
                    r = await cdp.send("Page.captureScreenshot", {"format": "jpeg", "quality": 88, "optimizeForSpeed": True, "clip": {"x": sc[0], "y": sc[1], "width": 1440, "height": 810, "scale": 4 / 3}})
                except Exception:
                    await asyncio.sleep(0.05)
                    continue
                i = len(frames)
                (FR / f"{i:06d}.jpg").write_bytes(base64.b64decode(r["data"]))
                frames.append(round(time.time() - t.t0, 4))
        t.t0 = time.time()
        grabber = asyncio.ensure_future(grab())
        await asyncio.sleep(0.5)
        for ci, ch in enumerate(chapters):
            if only and ci not in only:
                continue
            t.ev("chapter", n=ci, title=ch["title"])
            for s in ch["steps"]:
                start = t.now()
                t.ev("step", id=s["id"], cap=s["cap"])
                try:
                    await s["act"](t)
                except Exception as e:
                    print("STEP FAIL", s["id"], repr(e)[:300], flush=True)
                    await page.screenshot(path=str(ROOT / f"fail_{s['id']}.jpg"), type="jpeg", quality=60)
                    for _ in range(2):
                        await page.keyboard.press("Escape")
                        await asyncio.sleep(0.3)
                left = start + durs.get(s["id"], 0) + 1.0 - t.now()
                if left > 0:
                    await asyncio.sleep(left)
                t.ev("step_end", id=s["id"])
                print("step", s["id"], round(t.now() - start, 1), flush=True)
            await asyncio.sleep(0.4)
        state["on"] = False
        await grabber
        t.ev("end")
        await b.close()
    (ROOT / "rec.json").write_text(json.dumps({"log": log, "frames": frames}))
    print("FRAMES", len(frames), "DUR", log[-1]["t"])


if __name__ == "__main__":
    from steps import CHAPTERS
    durs = json.loads((ROOT / "vo_durs.json").read_text()) if (ROOT / "vo_durs.json").exists() else {}
    only = [int(a) for a in sys.argv[1:]] or None
    asyncio.run(record(CHAPTERS, durs, only))
