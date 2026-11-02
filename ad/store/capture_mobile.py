import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

BASE = "https://gym-hub-demo.preview.emergentagent.com"
LOCAL = "http://127.0.0.1:8002"
OUT = Path(__file__).parent / "screens"
OUT.mkdir(exist_ok=True)


async def route_api(route):
    url = route.request.url.replace(BASE, LOCAL)
    resp = await route.fetch(url=url)
    await route.fulfill(response=resp)


async def tab(page, label):
    await page.get_by_role("button", name=label, exact=True).first.click(force=True)
    await page.wait_for_timeout(2200)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        ctx = await b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True)
        await ctx.route(f"{BASE}/api/**", route_api)
        page = await ctx.new_page()
        await page.goto(f"{BASE}/m/welcome", wait_until="networkidle")
        st = await page.evaluate("""async (b) => (await fetch(b + '/api/auth/login', {method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body: JSON.stringify({identifier:'store@gymboss-sample.in', password:'StoreShots@2026'})})).status""", BASE)
        print("login", st)
        await page.evaluate("localStorage.setItem('gb-theme','light')")

        async def shot(name):
            await page.wait_for_timeout(1200)
            await page.screenshot(path=str(OUT / f"{name}.png"))
            print("shot", name, page.url)

        await page.goto(f"{BASE}/m/home", wait_until="networkidle"); await shot("1_home")
        await page.goto(f"{BASE}/m/attendance", wait_until="networkidle"); await shot("3_attendance")
        await page.goto(f"{BASE}/m/manage", wait_until="networkidle"); await page.wait_for_timeout(1500); await shot("2_members")
        try:
            await page.locator('[data-testid="m-chip-due"]').click(force=True)
            await page.wait_for_timeout(1500)
            await shot("5a_dues_list")
            await page.locator('[data-testid="m-members"] button, [data-testid="m-members"] [role="button"]').filter(has_text="₹").first.click(force=True)
            await page.wait_for_timeout(2000)
            await shot("5b_member_detail")
        except Exception as e:
            print("dues flow failed", e)
        for label, name in [("Plan / Catalogue", "4_plans"), ("Staff / Admin", "7_staff"), ("Reports", "6_reports"), ("Finance", "1b_finance")]:
            try:
                await page.goto(f"{BASE}/m/manage", wait_until="networkidle")
                await tab(page, label)
                await shot(name)
            except Exception as e:
                print("tab failed", label, e)
        await b.close()

asyncio.run(main())
