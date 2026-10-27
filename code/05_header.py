"""Step 5. Make header.png (1200x630 social card) with Playwright: every ringfort as a dot,
coloured by what its notes say now.

Usage: python3 code/05_header.py [--vendor DIR]
(--vendor: folder with the Fraunces, Source Serif 4 and IBM Plex Mono TTFs, where Google Fonts is unreachable.)
"""
import asyncio
import json
import os
import sys

from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = json.load(open(os.path.join(ROOT, "data", "results.json")))
S = json.load(open(os.path.join(ROOT, "_work", "site_data.json")))
VENDOR = sys.argv[sys.argv.index("--vendor") + 1] if "--vendor" in sys.argv else None
pts = [[p[0], p[1], p[4]] for p in S["pts"] if p[2] == 0]
import random  # noqa: E402
random.Random(1).shuffle(pts)  # random drawing order, so no colour sits on top of the others

HTML = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,900&family=IBM+Plex+Mono:wght@400;500&family=Source+Serif+4:opsz,wght@8..60,400&display=swap">
<style>
body{margin:0;width:1200px;height:630px;background:#EEF1E4;color:#1C2216;overflow:hidden;position:relative;font-family:'Source Serif 4',Georgia,serif}
.l{position:absolute;left:68px;top:58px;width:660px}
.k{font:500 17px/1 'IBM Plex Mono',monospace;letter-spacing:.14em;text-transform:uppercase;color:#5E6852;display:flex;gap:14px;align-items:center}
.k b{background:#3E6B2A;color:#fff;padding:8px 10px;font-weight:500}
h1{font:900 82px/.92 'Fraunces',Georgia,serif;letter-spacing:-.02em;margin:24px 0 0}
h1 em{font-style:normal;color:#B3243A}
p{font-size:26px;line-height:1.36;margin:22px 0 0;color:#2E3826;max-width:600px}
.f{position:absolute;left:68px;bottom:34px;font:400 15px/1 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:#5E6852}
.lg{position:absolute;right:46px;bottom:30px;font:400 14px/1.6 'IBM Plex Mono',monospace;color:#5E6852;text-align:right}
.lg i{display:inline-block;width:11px;height:11px;border-radius:50%;margin:0 6px 0 14px;vertical-align:-1px}
canvas{position:absolute;right:24px;top:14px}
</style></head><body>
<div class="l"><div class="k"><b>Data study</b><span>History × data</span></div>
<h1>Did <em>fairy</em> belief protect Ireland's ringforts?</h1>
<p>__DEK__</p></div>
<div class="f">Dr Tristan Hotham · Independent researcher</div>
<div class="lg"><i style="background:#3E6B2A"></i>visible<i style="background:#B07A1C"></i>damaged<i style="background:#B3243A"></i>no visible trace</div>
<canvas id="c" width="900" height="1140" style="width:450px;height:570px"></canvas>
<script>
const P = __PTS__;
const C = ["#3E6B2A","#B07A1C","#B3243A","#AEB79C"];
const cv = document.getElementById("c"), x = cv.getContext("2d"); x.scale(2, 2);
const k = Math.cos(53.4 * Math.PI / 180), lo0 = -10.7, lo1 = -5.9, la0 = 51.35, la1 = 55.45;
const sc = Math.min(450 / ((lo1 - lo0) * k), 570 / (la1 - la0));
const X = l => (l - lo0) * k * sc, Y = l => (la1 - l) * sc;
for (const p of P) { const o = p[2]; x.beginPath(); x.arc(X(p[1]), Y(p[0]), 1.1, 0, 6.2832); x.fillStyle = C[o]; x.globalAlpha = o === 3 ? .5 : .85; x.fill(); }
</script></body></html>"""
dek = (f"{R['n_group']['ringfort']:,} ringforts in the national record, set against barrows, "
       "enclosures and moated sites. The fairies left few fingerprints.")
html = HTML.replace("__PTS__", json.dumps(pts, separators=(",", ":"))).replace("__DEK__", dek)
tmp = os.path.join(ROOT, "_work", "_header_tmp.html")
open(tmp, "w", encoding="utf-8").write(html)


def fontcss():
    v = VENDOR
    return (f"@font-face{{font-family:'Fraunces';font-weight:100 900;src:url(file://{v}/Fraunces[SOFT,WONK,opsz,wght].ttf)}}"
            f"@font-face{{font-family:'Source Serif 4';font-weight:200 900;src:url(file://{v}/SourceSerif4[opsz,wght].ttf)}}"
            f"@font-face{{font-family:'IBM Plex Mono';font-weight:400;src:url(file://{v}/IBMPlexMono-Regular.ttf)}}"
            f"@font-face{{font-family:'IBM Plex Mono';font-weight:500;src:url(file://{v}/IBMPlexMono-Medium.ttf)}}")


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1200, "height": 630})
        if VENDOR:
            css = fontcss()

            async def route(r):
                if "fonts.googleapis.com" in r.request.url:
                    return await r.fulfill(body=css, content_type="text/css")
                return await r.continue_()
            await pg.route("**/*", route)
        await pg.goto("file://" + tmp)
        await pg.wait_for_timeout(1500)
        await pg.screenshot(path=os.path.join(ROOT, "header.png"))
        await b.close()

asyncio.run(main())
os.remove(tmp)
print("header.png written")
