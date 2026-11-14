import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

URL = "https://gymboss-preview--66rae3xb.preview.emergentagent.com"
OUT = Path(__file__).parent / "tour"
OUT.mkdir(exist_ok=True)
PAGES = ["dashboard", "members", "attendance", "plans", "payments", "enquiries", "expenses", "outlets", "staff", "finance", "reports",
         "export-center", "announcements", "settings", "subscription", "support", "profile"]


async def login(page):
    await page.goto(URL + "/login")
    await page.fill('[data-testid="login-identifier"]', "demo@gymbossvvo.in")
    await page.fill('[data-testid="login-password"]', "Demo@2026")
    await page.click('[data-testid="login-submit-button"]')
    await page.wait_for_url("**/app/**", timeout=30000)


async def main(pages):
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        page = await b.new_page(viewport={"width": 1440, "height": 810}, device_scale_factor=4/3)
        await login(page)
        for p in pages:
            await page.goto(f"{URL}/app/{p}")
            await page.wait_for_timeout(2500)
            await page.screenshot(path=str(OUT / f"{p}.jpg"), type="jpeg", quality=70)
            print(p, flush=True)
        await b.close()

asyncio.run(main(sys.argv[1:] or PAGES))
