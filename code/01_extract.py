"""Step 1. Read the Sites and Monuments Record (SMR) for the Republic of Ireland and write one row
per earthwork in the comparison set, with map depictions, note-based condition, folklore mentions,
townland name elements, elevation and slope.

Input (read in place, not copied):
  /home/claude/hist/_data10/ireland_smr_all.json.gz   National Monuments Service SMR, CC BY 4.0
  /mnt/user-data/uploads/Downloads/hist_dem_z10.bin  AWS Terrain Tiles (Mapzen/Tilezen), zoom 10
  /home/claude/hist/_data3/ne/geojson/ne_10m_admin_0_countries.geojson  Natural Earth (public domain)

Output:
  data/sites.csv           one row per earthwork in scope (see README for columns)
  data/class_counts.csv    every SMR monument class with its count
  _work/outlines.json      Natural Earth outlines of Ireland and the UK (working file)

Usage: python3 code/01_extract.py
"""
import collections
import gzip
import json
import os
import re
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from notes_rules import status, folk, usable  # noqa: E402
from dem import DEM  # noqa: E402

SMR = os.environ.get("SMR", "/home/claude/hist/_data10/ireland_smr_all.json.gz")
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "_work"), exist_ok=True)

recs = json.load(gzip.open(SMR))
print(len(recs), "SMR records")

cc = collections.Counter(r["MONUMENT_CLASS"] for r in recs)
pd.DataFrame(cc.most_common(), columns=["monument_class", "n"]).to_csv(os.path.join(ROOT, "data", "class_counts.csv"), index=False)


def group(cls):
    if cls.startswith("Ringfort"):
        return "ringfort"
    if cls == "Enclosure":
        return "enclosure"
    if cls.startswith("Barrow"):
        return "barrow"
    if cls == "Moated site":
        return "moated site"
    if cls == "Earthwork":
        return "earthwork"
    if cls == "Mound":
        return "mound"
    if cls == "Souterrain":
        return "souterrain"
    if cls == "Fulacht fia":
        return "fulacht fia"
    return None


UNKNOWN = {"", "null", "none", "n/a"}
NOT_RE = re.compile(r"^(?:no[a-z]* ?i[a-z]*|not (?:shown|marked|depicted|located|on map|visible)|not in[a-z]*|no indicated|ìndicated)$")
PLAIN = re.compile(r"^(?:hachured|indicated|outlined|partially (?:hachured|indicated|outlined)|dotted outline|faint enclosure|"
                   r"(?:double |multivallate |bivallate )?(?:embanked )?en\w+re|embanked en\w+|hachured ?- ?indicated|in[a-z]*ted|indicted|indictaed|copse|enclosure)$")


def edition(v):
    """(depicted, labelled) from an SMR edition field. depicted: 1, 0 or None (unknown)."""
    s = re.sub(r"\(.*?\)", "", v or "").strip().strip(".").strip().lower()
    if s in UNKNOWN:
        return None, None
    if NOT_RE.match(s):
        return 0, 0
    if PLAIN.match(s):
        return 1, 0
    return 1, 1  # a name or word written on the map ('Fort', 'Lisheen', 'Rathmore', 'Cashel'...)


FIRST_YES = re.compile(r"(?:shown|marked|depicted|indicated|hachured|represented|appears|named|labelled|illustrated|recorded)\b[^.;]{0,80}?\bon (?:the |both |all )?(?:1st|first|18[2-4]\d)", re.I)
FIRST_NO = re.compile(r"not (?:shown|marked|depicted|indicated|represented|named|recorded|illustrated)\b[^.;]{0,40}?\bon (?:the |any )?(?:1st|first|18[2-4]\d|any|os)", re.I)


def first_from_notes(n):
    if not usable(n):
        return None
    no = FIRST_NO.search(n)
    yes = FIRST_YES.search(n)
    if no and (not yes or no.start() <= yes.start()):
        return 0
    if yes:
        return 1
    return None


def townland_element(t):
    t = (t or "").upper().strip()
    if re.match(r"^(?:LIS|LIOS|LISS)", t):
        return "lis"
    if re.match(r"^(?:RATH|RAHEEN|RAHEENS|RAHEENA)", t) or re.search(r"\bRATH\b", t):
        return "rath"
    if re.match(r"^(?:CAHER|CAHIR|CATHAIR|CASHEL)", t):
        return "caher"
    return ""


rows = []
for r in recs:
    g = group(r["MONUMENT_CLASS"])
    if g is None:
        continue
    lat, lon = r["LATITUDE"], r["LONGITUDE"]
    if lat is None or lon is None:
        continue
    n = r["WEB_NOTES"] or ""
    f_dep, f_lab = edition(r["FIRST_EDITION"])
    f_src = "field" if f_dep is not None else ""
    if f_dep is None:
        f_dep = first_from_notes(n)
        f_src = "notes" if f_dep is not None else ""
    l_dep, l_lab = edition(r["LATEST_EDITION"])
    st, ev = status(n)
    fk = folk(n)
    yr = re.search(r"\((\d{4})\)", r["LATEST_EDITION"] or "")
    rows.append(dict(
        id=r["ENTITY_ID"], cls=r["MONUMENT_CLASS"], group=g, county=r["COUNTY"].title(), townland=(r["TOWNLAND"] or "").title(),
        lat=round(lat, 5), lon=round(lon, 5),
        first_ed=(r["FIRST_EDITION"] or "").strip(), first_dep=f_dep, first_dep_src=f_src, first_labelled=f_lab,
        latest_ed=(r["LATEST_EDITION"] or "").strip(), latest_dep=l_dep, latest_year=int(yr.group(1)) if yr else None,
        notes=1 if usable(n) else 0, status=st or "", status_evidence=ev[:200],
        folk=1 if fk else (0 if fk == "" else None), folk_snippet=(fk or "")[:820],
        townland_el=townland_element(r["TOWNLAND"]),
    ))
d = pd.DataFrame(rows)
print(d.group.value_counts())

# elevation and slope from the zoom-10 terrain tiles (about 92 m pixels at Irish latitudes)
dem = DEM()
gx, gy = dem.to_pix(d.lat.values, d.lon.values)
d["elev_m"] = np.round(dem.bilinear(gx, gy), 1)
latr = np.radians(d.lat.values)
pix_m = 2 * np.pi * 6378137 * np.cos(latr) / (256 * 2 ** 10)
dzdx = (dem.bilinear(gx + 1, gy) - dem.bilinear(gx - 1, gy)) / (2 * pix_m)
dzdy = (dem.bilinear(gx, gy + 1) - dem.bilinear(gx, gy - 1)) / (2 * pix_m)
d["slope_deg"] = np.round(np.degrees(np.arctan(np.hypot(dzdx, dzdy))), 2)

for c in ["first_dep", "first_labelled", "latest_dep", "latest_year", "folk"]:
    d[c] = d[c].astype("Int64")
d.to_csv(os.path.join(ROOT, "data", "sites.csv"), index=False)
print("sites.csv", len(d), os.path.getsize(os.path.join(ROOT, "data", "sites.csv")) // 1024, "KB")

# outline of the Republic of Ireland for maps (Natural Earth 10m)
ne = json.load(open("/home/claude/hist/_data3/ne/geojson/ne_10m_admin_0_countries.geojson"))
ie = [f for f in ne["features"] if f["properties"].get("ADMIN") == "Ireland"][0]["geometry"]
uk = [f for f in ne["features"] if f["properties"].get("ADMIN") == "United Kingdom"][0]["geometry"]
json.dump({"ie": ie, "uk": uk}, open(os.path.join(ROOT, "_work", "outlines.json"), "w"))
print("done")
