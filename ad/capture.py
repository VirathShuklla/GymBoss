import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

BASE = "https://gym-hub-demo.preview.emergentagent.com"
OUT = Path(__file__).parent / "assets" / "screens"
OUT.mkdir(parents=True, exist_ok=True)
WEB = ["dashboard", "members", "attendance", "payments", "finance", "reports", "plans"]
MOB = ["m/home", "m/attendance", "m/manage"]


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 1600, "height": 1000}, device_scale_factor=1.25)
        r = await ctx.request.post(f"{BASE}/api/auth/login", data={"identifier": "demo@gymbossvvo.in", "password": "Demo@2026"})
        print("login", r.status)
        page = await ctx.new_page()
        for s in WEB:
            await page.goto(f"{BASE}/app/{s}", wait_until="networkidle")
            await page.wait_for_timeout(2500)
            await page.screenshot(path=str(OUT / f"web_{s}.png"))
            print("web", s, page.url)
        mctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2.5, storage_state=await ctx.storage_state())
        mp = await mctx.new_page()
        for s in MOB:
            await mp.goto(f"{BASE}/{s}", wait_until="networkidle")
            await mp.wait_for_timeout(2500)
            await mp.screenshot(path=str(OUT / f"mob_{s.split('/')[-1]}.png"))
            print("mob", s, mp.url)
        await b.close()

asyncio.run(main())
