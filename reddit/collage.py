"""Reddit (r/dataisbeautiful) collage for Fairy Forts. 2400 x 3000 px.
Reads ../data/results.json, ../data/sites.csv and ../_work/outlines.json (from code/01_extract.py).
Usage: cd reddit && python3 collage.py [FONT_DIR]
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
F = sys.argv[1] if len(sys.argv) > 1 else "/tmp/claude-0/-home-claude/c232619d-81e0-53f3-9de6-41e973630753/scratchpad/fonts/"
for f in ["FrauncesVar.ttf", "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf", "SourceSerif4-Regular.ttf", "SourceSerif4-Semibold.ttf", "SourceSerif4-It.ttf"]:
    fm.fontManager.addfont(os.path.join(F, f))
DISP = fm.FontProperties(fname=os.path.join(F, "FrauncesVar.ttf"), weight=900)
SER, MONO = "Source Serif 4", "IBM Plex Mono"
BG, FG, MUT = "#EEF1E4", "#1C2216", "#5E6852"
LAND, MOSS, OCHRE, BERRY, NONE, GREY = "#DEE5CC", "#3E6B2A", "#B07A1C", "#B3243A", "#B7BFA6", "#7C8770"
R = json.load(open(os.path.join(ROOT, "data", "results.json")))
d = pd.read_csv(os.path.join(ROOT, "data", "sites.csv"), usecols=["group", "lat", "lon", "status"])
OL = json.load(open(os.path.join(ROOT, "_work", "outlines.json")))
K = np.cos(np.radians(53.4))

fig = plt.figure(figsize=(12, 15), dpi=200, facecolor=BG)
fig.text(0.045, 0.967, "Did fairies save Ireland's ringforts?", fontproperties=DISP, fontsize=40, color=FG, va="top")
fig.text(0.045, 0.918, f"Ireland's {R['n_group']['ringfort']:,} ringforts are ‘fairy forts’ that it was unlucky to disturb. I set every one in the\n"
         "national monuments record against other earthworks, from the 1840s Ordnance Survey maps to today.",
         family=SER, fontsize=15, color=FG, va="top", linespacing=1.4)

# hero map
ax = fig.add_axes([0.01, 0.36, 0.57, 0.505])
cs = OL["ie"]["coordinates"]
for p in cs:
    a = np.array(p[0]); ax.fill(a[:, 0], a[:, 1], fc=LAND, ec="#C6CFB0", lw=0.8, zorder=0)
rf = d[d.group == "ringfort"].sample(frac=1, random_state=3)
col = rf.status.map({"visible": MOSS, "damaged": OCHRE, "gone": BERRY}).fillna(NONE)
ax.scatter(rf.lon, rf.lat, s=1.7, c=col, lw=0, alpha=.9, rasterized=True)
ax.set_xlim(-10.75, -5.9); ax.set_ylim(51.35, 55.45); ax.set_aspect(1 / K); ax.axis("off")
cnt = R["ringfort_status_counts"]
lx, ly = 0.05, 0.318
fig.text(lx, ly + 0.026, "EVERY RINGFORT, BY WHAT ITS SURVEY NOTES SAY NOW", family=MONO, fontsize=10, color=MUT)
for i, (lab, c, k) in enumerate([("still visible", MOSS, "visible"), ("damaged", OCHRE, "damaged"), ("no visible trace", BERRY, "gone"), ("notes not online", NONE, "none")]):
    x = lx + (i % 2) * 0.25; y = ly - (i // 2) * 0.022
    fig.patches.append(matplotlib.patches.Circle((x + 0.006, y + 0.005), 0.0055, transform=fig.transFigure, fc=c, ec="none"))
    fig.text(x + 0.018, y, f"{lab}  {cnt[k]:,}", family=MONO, fontsize=11.5, color=FG)

# right column numbers
tx = fig.add_axes([0.60, 0.35, 0.37, 0.505]); tx.axis("off")
mg = R["map_by_group"]; pa = R["map_pooled_adjusted"]
notes = [(f"{mg['ringfort']['share'] * 100:.1f}%", MOSS, f"of ringforts drawn on the c.1840 map were\nstill drawn about 80 years later. Barrows,\nwhich are not fairy forts: {mg['barrow']['share'] * 100:.1f}%."),
         (f"{R['gone_by_class_1840']['Ringfort - unclassified']['share'] * 100:.0f}%", OCHRE, "of 'unclassified' ringforts drawn c.1840 have\ngone, against {:.0f}% of raths. A site must\nsurvive well to be called a ringfort at all.".format(R["gone_by_class_1840"]["Ringfort - rath"]["share"] * 100)),
         (f"{pa['round earthwork'] * 100:.1f}%", BERRY, f"of all round earthworks (ringforts and\nenclosures together) stayed on the map,\nagainst {pa['barrow'] * 100:.1f}% for barrows. No fairy premium."),
         (f"{R['folk']['ringfort_n']} of {R['folk']['ringfort_notes']:,}", FG, "ringfort survey notes mention fairies,\nsuperstition or bad luck.")]
for (big, c, small), y in zip(notes, [1.0, 0.74, 0.48, 0.22]):
    tx.text(0, y, big, fontproperties=DISP, fontsize=31, color=c, va="top", transform=tx.transAxes)
    tx.text(0, y - 0.085, small, family=SER, fontsize=12.5, color=FG, va="top", transform=tx.transAxes, linespacing=1.3)

# bottom left: still on the map, by kind of earthwork
fig.text(0.05, 0.268, "STILL ON THE MAP, c.1840 TO c.1920 (adjusted for county, height, slope)", family=MONO, fontsize=10, color=MUT)
bx = fig.add_axes([0.21, 0.085, 0.29, 0.17], facecolor=BG)
rows = [("Ringforts + enclosures", pa["round earthwork"], OCHRE), ("Ringforts", R["map_adjusted"]["ringfort"], MOSS), ("Barrows", R["map_adjusted"]["barrow"], GREY),
        ("Moated sites", R["map_adjusted"]["moated site"], GREY), ("Mounds", R["map_adjusted"]["mound"], GREY), ("Enclosures", R["map_adjusted"]["enclosure"], GREY),
        ("Earthworks", R["map_adjusted"]["earthwork"], GREY)]
y = np.arange(len(rows))[::-1]
bx.barh(y, [r[1] for r in rows], color=[r[2] for r in rows], height=.66)
for yi, r in zip(y, rows):
    bx.text(r[1] + .02, yi, f"{r[1] * 100:.1f}%", va="center", family=MONO, fontsize=10.5, color=FG)
bx.set_yticks(y); bx.set_yticklabels([r[0] for r in rows], family=MONO, fontsize=11, color=FG)
bx.set_xlim(0, 1.15); bx.set_xticks([])
for s in ["top", "right", "bottom"]:
    bx.spines[s].set_visible(False)
bx.spines["left"].set_color(MUT); bx.tick_params(length=0)

# bottom right: elevation
fig.text(0.585, 0.268, "NO VISIBLE TRACE TODAY, BY HEIGHT", family=MONO, fontsize=10, color=MUT)
ex = fig.add_axes([0.61, 0.10, 0.34, 0.155], facecolor=BG)
E = R["elev_bands"]; x = np.arange(len(E))
for k, c, n in [("gone_enclosure", GREY, "enclosures"), ("gone_ringfort", BERRY, "ringforts")]:
    v = [e[k]["share"] for e in E]
    ex.plot(x, v, color=c, lw=3, marker="o", ms=7)
    ex.text(x[-1] + 0.15, v[-1], n, family=MONO, fontsize=11, color=c, va="center")
ex.set_xticks(x); ex.set_xticklabels(["<50 m", "50+", "100+", "150+", "200+"], family=MONO, fontsize=10.5, color=FG)
ex.set_ylim(0, .55); ex.set_yticks([0, .2, .4]); ex.set_yticklabels(["0%", "20%", "40%"], family=MONO, fontsize=10.5, color=FG)
ex.set_xlim(-.3, len(E) + .4)
ex.grid(axis="y", color="#CDD5BB", lw=.8); ex.set_axisbelow(True)
for s in ["top", "right"]:
    ex.spines[s].set_visible(False)
ex.spines["left"].set_color(MUT); ex.spines["bottom"].set_color(MUT); ex.tick_params(length=0)

fig.text(0.045, 0.012, "Data: Sites and Monuments Record, National Monuments Service, Department of Housing, Local Government and Heritage (CC BY 4.0).\n"
         "Republic of Ireland only. Survival read from OS map depictions and survey notes: proxies, and classes partly depend on survival.\n"
         "Analysis and chart: Tristan Hotham, with Python and matplotlib. tristan-hotham.github.io/fairy-forts",
         family=MONO, fontsize=9, color=MUT, linespacing=1.45)
fig.savefig(os.path.join(HERE, "fairy_forts.png"), facecolor=BG, dpi=200)
print("ok")
