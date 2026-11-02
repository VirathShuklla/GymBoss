import asyncio
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright

ROOT = Path(__file__).parent
OUT = ROOT / "playstore"
OUT.mkdir(exist_ok=True)
NAMES = ["01_dashboard_collections", "02_member_management", "03_attendance_qr", "04_plans_renewals", "05_payments_dues", "06_reports", "07_staff_access"]


async def snap(b, query, size, dest):
    page = await b.new_page(viewport={"width": size[0], "height": size[1]})
    await page.goto(f"file://{ROOT}/store.html?{query}")
    await page.evaluate("window.READY")
    await page.wait_for_timeout(500)
    tmp = ROOT / "tmp.png"
    await page.screenshot(path=str(tmp))
    await page.close()
    Image.open(tmp).convert("RGB").save(dest, optimize=True)
    tmp.unlink()
    print(dest.name, Image.open(dest).size, round(dest.stat().st_size / 1024), "KB")


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for i, n in enumerate(NAMES):
            await snap(b, f"i={i}", (1080, 1920), OUT / f"{n}.png")
        await snap(b, "feature=1", (1024, 500), OUT / "feature_graphic_1024x500.png")
        await b.close()

asyncio.run(main())
