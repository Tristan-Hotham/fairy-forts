"""Render index.html with Playwright Chromium at 1280px and 390px, light and dark, for checking.
Screenshots go to _shots/ (not part of the published site; delete after checking).

Usage: python3 code/shots.py [--vendor DIR]

Where Google Fonts and cdnjs are unreachable, pass --vendor with a folder holding the font files
(Fraunces, Source Serif 4, IBM Plex Mono TTFs) and leaflet/dist/. Map tiles are blocked.
"""
import asyncio
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = sys.argv[sys.argv.index("--vendor") + 1] if "--vendor" in sys.argv else None
OUT = os.path.join(ROOT, "_shots")
os.makedirs(OUT, exist_ok=True)
WIDTHS = [int(w) for w in os.environ.get("WIDTHS", "1280,390").split(",")]
THEMES = os.environ.get("THEMES", "light,dark").split(",")


def fontcss():
    v = VENDOR
    return (f"@font-face{{font-family:'Fraunces';font-weight:100 900;src:url(file://{v}/Fraunces[SOFT,WONK,opsz,wght].ttf)}}"
            f"@font-face{{font-family:'Source Serif 4';font-weight:200 900;src:url(file://{v}/SourceSerif4[opsz,wght].ttf)}}"
            f"@font-face{{font-family:'Source Serif 4';font-style:italic;font-weight:200 900;src:url(file://{v}/SourceSerif4-Italic[opsz,wght].ttf)}}"
            f"@font-face{{font-family:'IBM Plex Mono';font-weight:400;src:url(file://{v}/IBMPlexMono-Regular.ttf)}}"
            f"@font-face{{font-family:'IBM Plex Mono';font-weight:500;src:url(file://{v}/IBMPlexMono-Medium.ttf)}}")


async def route(r):
    u = r.request.url
    if VENDOR and "fonts.googleapis.com" in u:
        return await r.fulfill(body=fontcss(), content_type="text/css")
    if VENDOR and "leaflet.min.js" in u:
        return await r.fulfill(path=os.path.join(VENDOR, "leaflet", "dist", "leaflet.js"), content_type="application/javascript")
    if VENDOR and "leaflet.min.css" in u:
        return await r.fulfill(path=os.path.join(VENDOR, "leaflet", "dist", "leaflet.css"), content_type="text/css")
    if u.startswith("file://"):
        return await r.continue_()
    return await r.abort()


async def shoot(b, width, theme):
    ctx = await b.new_context(viewport={"width": width, "height": 900}, color_scheme=theme, device_scale_factor=1)
    pg = await ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" and "ERR_FAILED" not in m.text else None)
    await pg.route("**/*", route)
    await pg.goto("file://" + os.path.join(ROOT, "index.html"))
    await pg.wait_for_timeout(3000)
    sw = await pg.evaluate("document.documentElement.scrollWidth")
    tag = f"{width}_{theme}"
    await pg.screenshot(path=os.path.join(OUT, f"full_{tag}.png"), full_page=True)
    fig = await pg.query_selector(".figure.bleed")
    await fig.scroll_into_view_if_needed()
    await fig.screenshot(path=os.path.join(OUT, f"map_dots_{tag}.png"))
    for lay in ["map", "dens", "lost"]:
        await pg.click(f'[data-layer="{lay}"]')
        await pg.wait_for_timeout(600)
        await fig.screenshot(path=os.path.join(OUT, f"map_{lay}_{tag}.png"))
    print(tag, "scrollWidth", sw, "errors", errs[:5])
    await ctx.close()


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for w in WIDTHS:
            for t in THEMES:
                await shoot(b, w, t)
        await b.close()

if __name__ == "__main__":
    asyncio.run(main())
