"""Step 3. Analysis. Reads data/sites.csv, data/county_areas.csv, data/gb_folk_names.csv and
data/validation_sample.csv; writes data/results.json (every number used anywhere), data/county_summary.csv,
data/hex_grid.geojson, data/group_survival.csv, data/folklore_notes.csv and _work/site_data.json
(compact data for the page, deleted by step 4).

Two survival measures:
  MAP   among sites drawn on the first edition OS 6-inch map (c.1840), the share still drawn on the
        latest edition in the record (mostly revised in the early 20th century).
  NOTES among sites with real notes, the share whose notes say no visible surface trace remains
        (levelled, destroyed, removed, not visible at ground level, known only from aerial images).
Comparisons are raw shares and shares standardised by logistic regression with county fixed effects,
elevation and slope (marginal standardisation: predict every site as each group, then average).

Usage: python3 code/03_analyse.py
"""
import json
import math
import os

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from pyproj import Transformer
from shapely.geometry import Polygon, shape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")
W = os.path.join(ROOT, "_work")
d = pd.read_csv(os.path.join(D, "sites.csv"), dtype={"townland_el": str}, keep_default_na=True)
d["townland_el"] = d.townland_el.fillna("")
d["county26"] = d.county.replace({"Tipperary North": "Tipperary", "Tipperary South": "Tipperary"})
R = {}
# The notes mention the c.1840 map far more often when a site has since gone (a levelled site is described
# by its old depiction), so a first-edition flag read from the notes is biased. Only the SMR's own
# FIRST_EDITION field is used for the c.1840 depiction.
R["first_dep_from_notes_ignored"] = int((d.first_dep_src == "notes").sum())
d.loc[d.first_dep_src == "notes", "first_dep"] = np.nan


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(c - h, 4), round(c + h, 4)]


def share(s):
    s = s.dropna()
    k, n = int(s.sum()), int(len(s))
    return {"n": n, "k": k, "share": round(k / n, 4) if n else None, "ci": wilson(k, n)}


# ---------- the record ----------
cc = pd.read_csv(os.path.join(D, "class_counts.csv"))
R["smr_total"] = int(cc.n.sum())
R["smr_classes"] = int(len(cc))
R["n_group"] = {k: int(v) for k, v in d.group.value_counts().items()}
R["n_class"] = {k: int(v) for k, v in d[d.group == "ringfort"].cls.value_counts().items()}
R["ringfort_share_of_smr"] = round(R["n_group"]["ringfort"] / R["smr_total"], 4)
R["earthworks_in_scope"] = int(len(d))

# notes: usable vs placeholder
noteable = d[d.group.isin(["ringfort", "enclosure", "souterrain"])]
R["notes"] = {g: {"n": int(len(x)), "usable": int(x.notes.sum()), "placeholder": int(len(x) - x.notes.sum()),
                  "placeholder_share": round(1 - x.notes.mean(), 4)} for g, x in noteable.groupby("group")}
R["notes_none_for"] = ["barrow", "moated site", "earthwork", "mound", "fulacht fia"]

# validation of the notes rules
v = pd.read_csv(os.path.join(D, "validation_sample.csv"))
R["validation"] = {"n": int(len(v)), "agree": int(v.agree.sum()), "share": round(v.agree.mean(), 4),
                   "false_gone": int(((v.rule_gone == "gone") & (v.reader_gone == "not gone")).sum()),
                   "missed_gone": int(((v.rule_gone == "not gone") & (v.reader_gone == "gone")).sum())}

# ---------- density ----------
areas = pd.read_csv(os.path.join(D, "county_areas.csv"))
R["state_area_km2"] = int(areas.area_km2.sum())
rf = d[d.group == "ringfort"]
R["ringforts_per_km2"] = round(len(rf) / R["state_area_km2"], 3)
R["km2_per_ringfort"] = round(R["state_area_km2"] / len(rf), 2)

# ---------- survival measures ----------
d["map_kept"] = np.where((d.first_dep == 1) & d.latest_dep.notna(), d.latest_dep, np.nan)
d["gone"] = np.where(d.notes == 1, (d.status == "gone").astype(float), np.nan)
d["gone_or_damaged"] = np.where(d.notes == 1, d.status.isin(["gone", "damaged"]).astype(float), np.nan)
d["elev100"] = d.elev_m.clip(lower=0) / 100
d["first1840"] = (d.first_dep == 1).astype(int)

MAPG = ["ringfort", "barrow", "moated site", "mound", "enclosure", "earthwork", "souterrain"]
R["map_by_group"] = {g: share(d.loc[d.group == g, "map_kept"]) for g in MAPG + ["fulacht fia"]}
R["map_by_class"] = {c: share(d.loc[d.cls == c, "map_kept"]) for c in R["n_class"]}
R["first_dep_by_group"] = {g: {"drawn": int((x.first_dep == 1).sum()), "not": int((x.first_dep == 0).sum()),
                               "unknown": int(x.first_dep.isna().sum()), "from_notes": int((x.first_dep_src == "notes").sum())}
                           for g, x in d.groupby("group")}
ly = d.loc[(d.map_kept.notna()) & d.latest_year.notna(), "latest_year"]
R["latest_year"] = {"n_with_year": int(len(ly)), "n_map": int(d.map_kept.notna().sum()), "median": int(ly.median()),
                    "q25": int(ly.quantile(.25)), "q75": int(ly.quantile(.75))}

NG = ["ringfort", "enclosure", "souterrain"]
R["gone_by_group_all"] = {g: share(d.loc[d.group == g, "gone"]) for g in NG}
R["gone_by_group_1840"] = {g: share(d.loc[(d.group == g) & (d.first_dep == 1), "gone"]) for g in NG}
R["gone_by_class_1840"] = {c: share(d.loc[(d.cls == c) & (d.first_dep == 1), "gone"]) for c in list(R["n_class"]) + ["Enclosure"]}
R["damaged_or_gone_1840"] = {g: share(d.loc[(d.group == g) & (d.first_dep == 1), "gone_or_damaged"]) for g in ["ringfort", "enclosure"]}
R["gone_ringfort_notdrawn"] = share(d.loc[(d.group == "ringfort") & (d.first_dep == 0), "gone"])
R["gone_enclosure_notdrawn"] = share(d.loc[(d.group == "enclosure") & (d.first_dep == 0), "gone"])
R["ringfort_status_counts"] = {k: int(v) for k, v in d.loc[d.group == "ringfort", "status"].fillna("none").value_counts().items()}


def standardise(df, y, var, levels, extra=""):
    # counties with fewer than 30 sites, or with no variation in the outcome, are left out of the model
    st = df.groupby("county26")[y].agg(["size", "mean"])
    keep = st[(st["size"] >= 30) & (st["mean"] > 0) & (st["mean"] < 1)].index
    df = df[df.county26.isin(keep)]
    f = f"{y} ~ C({var}) + C(county26) + elev100 + slope_deg{extra}"
    m = smf.logit(f, data=df).fit(disp=0, maxiter=300)
    out = {}
    for lv in levels:
        dd = df.copy()
        dd[var] = lv
        out[lv] = round(float(m.predict(dd).mean()), 4)
    return m, out


# MAP model: ringfort against each comparison group
mm = d[d.map_kept.notna() & d.group.isin(MAPG)].copy()
m_map, adj_map = standardise(mm, "map_kept", "group", MAPG)
R["map_adjusted"] = adj_map
R["map_model_n"] = int(m_map.nobs)
R["map_or_vs_ringfort"] = {g: round(float(np.exp(m_map.params[f"C(group)[T.{g}]"])), 3)
                           for g in MAPG if f"C(group)[T.{g}]" in m_map.params}  # base level is alphabetical
R["map_or_base"] = sorted(MAPG)[0]

# pooled: ringforts and enclosures together as round earthworks, so the line between the two classes
# (which partly depends on survival) does not matter
POOLG = ["round earthwork", "barrow", "moated site", "mound", "earthwork"]
mp_ = mm[mm.group.isin(["ringfort", "enclosure", "barrow", "moated site", "mound", "earthwork"])].copy()
mp_["pgroup"] = mp_.group.replace({"ringfort": "round earthwork", "enclosure": "round earthwork"})
_, adj_pool = standardise(mp_, "map_kept", "pgroup", POOLG)
R["map_pooled_adjusted"] = adj_pool
R["map_pooled_raw"] = share(mp_.loc[mp_.pgroup == "round earthwork", "map_kept"])
R["premium_pooled_vs_barrow_pp"] = round((adj_pool["round earthwork"] - adj_pool["barrow"]) * 100, 1)
R["premium_pooled_vs_moated_pp"] = round((adj_pool["round earthwork"] - adj_pool["moated site"]) * 100, 1)
# pooled notes measure, for reference
R["gone_pooled_1840"] = share(d.loc[d.group.isin(["ringfort", "enclosure"]) & (d.first_dep == 1), "gone"])

# NOTES model: ringfort against enclosure, 1840-drawn sites
nm = d[d.gone.notna() & d.group.isin(["ringfort", "enclosure"]) & (d.first_dep == 1)].copy()
m_n, adj_n = standardise(nm, "gone", "group", ["ringfort", "enclosure"])
R["gone_adjusted_1840"] = adj_n
R["gone_model_n"] = int(m_n.nobs)
R["gone_or_ringfort_vs_enclosure"] = round(float(np.exp(-m_n.params["C(group)[T.ringfort]"])) ** -1, 3)
# elevation and slope effects (per 100 m, per degree) in the notes model
R["gone_or_per100m"] = round(float(np.exp(m_n.params["elev100"])), 3)
R["gone_or_per_degree"] = round(float(np.exp(m_n.params["slope_deg"])), 3)

# ---------- elevation and slope bands ----------
EB = [(-100, 50, "under 50 m"), (50, 100, "50 to 100 m"), (100, 150, "100 to 150 m"), (150, 200, "150 to 200 m"), (200, 2000, "200 m and over")]
d["eband"] = pd.cut(d.elev_m, [b[0] for b in EB] + [EB[-1][1]], labels=[b[2] for b in EB], right=False)
R["elev_bands"] = []
for lab in [b[2] for b in EB]:
    x = d[d.eband == lab]
    row = {"band": lab, "n_ringforts": int((x.group == "ringfort").sum())}
    for g in ["ringfort", "enclosure"]:
        row[f"gone_{g}"] = share(x.loc[(x.group == g) & (x.first_dep == 1), "gone"])
    row["map_ringfort"] = share(x.loc[x.group == "ringfort", "map_kept"])
    row["map_other"] = share(x.loc[x.group.isin(["barrow", "moated site", "mound", "enclosure", "earthwork"]), "map_kept"])
    R["elev_bands"].append(row)
R["ringfort_elev_median"] = round(float(rf.elev_m.median()), 1)
R["enclosure_elev_median"] = round(float(d.loc[d.group == "enclosure", "elev_m"].median()), 1)
SB = [(0, 1, "under 1 degree"), (1, 2, "1 to 2 degrees"), (2, 4, "2 to 4 degrees"), (4, 90, "4 degrees and over")]
d["sband"] = pd.cut(d.slope_deg, [b[0] for b in SB] + [90], labels=[b[2] for b in SB], right=False)
R["slope_bands"] = [{"band": lab, "gone_ringfort": share(d.loc[(d.sband == lab) & (d.group == "ringfort") & (d.first_dep == 1), "gone"]),
                     "gone_enclosure": share(d.loc[(d.sband == lab) & (d.group == "enclosure") & (d.first_dep == 1), "gone"])}
                    for lab in [b[2] for b in SB]]

# ---------- named on the 1840 map ----------
pool = d[d.group.isin(["ringfort", "enclosure"]) & (d.first_dep == 1) & (d.first_dep_src == "field")].copy()
R["labelled"] = {}
for lab, x in pool.groupby("first_labelled"):
    R["labelled"]["named" if lab == 1 else "unnamed"] = {"gone": share(x.gone), "map": share(x.map_kept),
                                                         "n": int(len(x)), "ringfort_share": round(float((x.group == "ringfort").mean()), 4)}
pl = pool[pool.gone.notna() & pool.first_labelled.notna()].copy()
pl["named"] = pl.first_labelled.astype(int).map({1: "named", 0: "unnamed"})
_, adj_lab = standardise(pl, "gone", "named", ["named", "unnamed"])
R["labelled_gone_adjusted"] = adj_lab
plr = pl[pl.group == "ringfort"].copy()
_, adj_lab_r = standardise(plr, "gone", "named", ["named", "unnamed"])
R["labelled_gone_adjusted_ringforts"] = adj_lab_r
R["labelled_gone_ringforts_raw"] = {k: share(x.gone) for k, x in plr.groupby("named")}
R["named_examples"] = pool.loc[pool.first_labelled == 1, "first_ed"].str.strip().value_counts().head(8).to_dict()

# ---------- townland names ----------
R["townland"] = {}
rft = d[d.group == "ringfort"].copy()
rft["tel"] = rft.townland_el.replace("", "other")
for k, x in rft.groupby("tel"):
    R["townland"][k] = {"n": int(len(x)), "gone_all": share(x.gone), "gone_1840": share(x.loc[x.first_dep == 1, "gone"]),
                        "map": share(x.map_kept)}
tt = rft[rft.gone.notna()].copy()
tt["fortname"] = np.where(tt.tel.isin(["lis", "rath", "caher"]), "fortname", "other")
_, adj_t = standardise(tt, "gone", "fortname", ["fortname", "other"])
R["townland_gone_adjusted"] = adj_t
R["townland_fortname_n"] = int((tt.fortname == "fortname").sum())
R["townland_fortname_gone_raw"] = share(tt.loc[tt.fortname == "fortname", "gone"])
R["townland_other_gone_raw"] = share(tt.loc[tt.fortname == "other", "gone"])
# do fort-named townlands hold more ringforts? share of all SMR townland names (distinct, by county) with a fort element
tl = d[["county", "townland", "townland_el"]].drop_duplicates()
R["townlands_distinct_in_scope"] = int(len(tl))
R["townlands_fortname_distinct"] = int((tl.townland_el != "").sum())

# ---------- folklore in the notes ----------
fk = d[(d.folk == 1)].copy()
R["folk"] = {"n": int(len(fk)), "by_group": {k: int(v) for k, v in fk.group.value_counts().items()},
             "notes_searched": int(d.loc[d.group.isin(NG), "notes"].sum()),
             "ringfort_n": int((fk.group == "ringfort").sum()),
             "ringfort_notes": int(rf.notes.sum()),
             "gone": share(fk.gone), "gone_ringfort": share(fk.loc[fk.group == "ringfort", "gone"])}
R["folk"]["per_10000_ringfort_notes"] = round(R["folk"]["ringfort_n"] / R["folk"]["ringfort_notes"] * 10000, 1)
fk[["id", "cls", "county", "townland", "lat", "lon", "status", "folk_snippet"]].to_csv(os.path.join(D, "folklore_notes.csv"), index=False)

# verbatim quotes for the page (start and end phrases located in the snippet)
QUOTES = [("TN00680", "The site was levelled", "left fallow."),
          ("OF01136", "The local landowner", "fairy fort."),
          ("CO05478", "No visible surface trace.", "ploughed it."),
          ("GA02126", "No visible surface trace", "till the field."),
          ("MA05990", "According to local tradition", "never disturbed."),
          ("OF05141", "According to local information", "in the 1960s."),
          ("WI03453", "It is said that a man", "never came back"),
          ("KK00340", "the place was dug up", "not very old!"),
          ("TS02047", "The monument has been incorporated", "Fairy hole\u2019.")]
R["quotes"] = []
for qid, a, b in QUOTES:
    row = fk[fk.id == qid].iloc[0]
    t = row.folk_snippet
    i = t.index(a)
    j = t.index(b, i) + len(b)
    R["quotes"].append({"id": qid, "text": t[i:j], "county": row.county, "townland": row.townland, "cls": row.cls,
                        "status": row.status})

# ---------- county summary ----------
rows = []
for c, x in d.groupby("county26"):
    a = int(areas.set_index("county").area_km2[c])
    r_ = x[x.group == "ringfort"]
    gr = r_.loc[r_.first_dep == 1, "gone"].dropna()
    ge = x.loc[(x.group == "enclosure") & (x.first_dep == 1), "gone"].dropna()
    mr = r_.map_kept.dropna()
    mo = x.loc[x.group.isin(["barrow", "moated site", "mound", "enclosure", "earthwork"]), "map_kept"].dropna()
    rows.append(dict(county=c, area_km2=a, ringforts=len(r_), raths=int((r_.cls == "Ringfort - rath").sum()),
                     cashels=int((r_.cls == "Ringfort - cashel").sum()), ringforts_per_km2=round(len(r_) / a, 3),
                     enclosures=int((x.group == "enclosure").sum()),
                     ringfort_notes=int(r_.notes.sum()), ringfort_placeholder_share=round(1 - r_.notes.mean(), 4),
                     ringfort_gone_all=round(r_.gone.mean(), 4) if r_.gone.notna().any() else None,
                     ringfort_gone_1840=round(gr.mean(), 4) if len(gr) else None, n_ringfort_gone_1840=len(gr),
                     enclosure_gone_1840=round(ge.mean(), 4) if len(ge) else None, n_enclosure_gone_1840=len(ge),
                     ringfort_map_kept=round(mr.mean(), 4) if len(mr) else None, n_ringfort_map=len(mr),
                     other_map_kept=round(mo.mean(), 4) if len(mo) else None, n_other_map=len(mo),
                     median_elev_m=round(float(r_.elev_m.median()), 1)))
cs = pd.DataFrame(rows)
cs["gap_gone_pp"] = ((cs.enclosure_gone_1840 - cs.ringfort_gone_1840) * 100).round(1)
cs["gap_map_pp"] = ((cs.ringfort_map_kept - cs.other_map_kept) * 100).round(1)
cs.loc[(cs.n_ringfort_gone_1840 < 50) | (cs.n_enclosure_gone_1840 < 30), "gap_gone_pp"] = np.nan
cs.loc[(cs.n_ringfort_map < 50) | (cs.n_other_map < 30), "gap_map_pp"] = np.nan
cs = cs.sort_values("ringforts_per_km2", ascending=False)
cs.to_csv(os.path.join(D, "county_summary.csv"), index=False)
R["counties"] = json.loads(cs.to_json(orient="records"))
R["county_densest"] = cs.iloc[0][["county", "ringforts_per_km2", "ringforts"]].to_dict()
R["county_sparsest"] = cs.iloc[-1][["county", "ringforts_per_km2", "ringforts"]].to_dict()
R["county_most_ringforts"] = cs.sort_values("ringforts").iloc[-1][["county", "ringforts"]].to_dict()
g = cs.dropna(subset=["gap_gone_pp"])
R["county_gap_gone"] = {"n": int(len(g)), "positive": int((g.gap_gone_pp > 0).sum()), "max": g.sort_values("gap_gone_pp").iloc[-1][["county", "gap_gone_pp"]].to_dict(),
                        "min": g.sort_values("gap_gone_pp").iloc[0][["county", "gap_gone_pp"]].to_dict(), "median": round(float(g.gap_gone_pp.median()), 1)}
gm = cs.dropna(subset=["gap_map_pp"])
R["county_gap_map"] = {"n": int(len(gm)), "positive": int((gm.gap_map_pp > 0).sum()), "median": round(float(gm.gap_map_pp.median()), 1),
                       "max": gm.sort_values("gap_map_pp").iloc[-1][["county", "gap_map_pp"]].to_dict(),
                       "min": gm.sort_values("gap_map_pp").iloc[0][["county", "gap_map_pp"]].to_dict()}
gc = cs[cs.n_ringfort_gone_1840 >= 50]
R["county_gone_max"] = gc.sort_values("ringfort_gone_1840").iloc[-1][["county", "ringfort_gone_1840", "n_ringfort_gone_1840"]].to_dict()
R["county_gone_min"] = gc.sort_values("ringfort_gone_1840").iloc[0][["county", "ringfort_gone_1840", "n_ringfort_gone_1840"]].to_dict()
R["county_placeholder_max"] = cs.sort_values("ringfort_placeholder_share").iloc[-1][["county", "ringfort_placeholder_share"]].to_dict()
for k in list(R):
    if isinstance(R[k], dict):
        R[k] = {kk: (int(vv) if isinstance(vv, (np.integer,)) else float(vv) if isinstance(vv, np.floating) else vv) for kk, vv in R[k].items()}

# ---------- hex grid (ITM, flat-topped hexes, 6 km side) ----------
to_itm = Transformer.from_crs(4326, 2157, always_xy=True)
to_ll = Transformer.from_crs(2157, 4326, always_xy=True)
ol = json.load(open(os.path.join(W, "outlines.json")))
import shapely  # noqa: E402
ie_itm = shapely.transform(shape(ol["ie"]), lambda c: np.column_stack(to_itm.transform(c[:, 0], c[:, 1]))).buffer(0)
S = 6000.0
hw, hh = 1.5 * S, math.sqrt(3) * S
X, Y = to_itm.transform(d.lon.values, d.lat.values)
col = np.round(X / hw).astype(int)
# axial rounding for flat-top hexes
q = (2 / 3 * X) / S
r_ = (-1 / 3 * X + math.sqrt(3) / 3 * Y) / S
cx, cz = q, r_
cy = -cx - cz
rx, ry, rz = np.round(cx), np.round(cy), np.round(cz)
dx, dy, dz = abs(rx - cx), abs(ry - cy), abs(rz - cz)
m1 = (dx > dy) & (dx > dz)
m2 = ~m1 & (dy > dz)
rx = np.where(m1, -ry - rz, rx)
rz = np.where(~m1 & ~m2, -rx - ry, rz)
d["hq"], d["hr"] = rx.astype(int), rz.astype(int)
feats = []
hexrows = []
for (hq_, hr_), x in d.groupby(["hq", "hr"]):
    cxm = S * 1.5 * hq_
    cym = S * math.sqrt(3) * (hr_ + hq_ / 2)
    poly = Polygon([(cxm + S * math.cos(math.radians(60 * i)), cym + S * math.sin(math.radians(60 * i))) for i in range(6)])
    land = poly.intersection(ie_itm).area / 1e6
    r0 = x[x.group == "ringfort"]
    if len(r0) == 0 or land < 5:
        continue
    gone = r0.gone.dropna()
    kept = r0.map_kept.dropna()
    lon, lat = to_ll.transform(*poly.exterior.xy)
    props = dict(q=int(hq_), r=int(hr_), land_km2=round(land, 1), ringforts=int(len(r0)), per_km2=round(len(r0) / land, 3),
                 notes=int(len(gone)), gone=int(gone.sum()), gone_share=round(gone.mean(), 3) if len(gone) >= 10 else None,
                 map_n=int(len(kept)), map_kept=round(kept.mean(), 3) if len(kept) >= 10 else None)
    hexrows.append(props)
    feats.append({"type": "Feature", "properties": props,
                  "geometry": {"type": "Polygon", "coordinates": [[[round(a, 4), round(b, 4)] for a, b in zip(lon, lat)]]}})
json.dump({"type": "FeatureCollection", "features": feats}, open(os.path.join(D, "hex_grid.geojson"), "w"), separators=(",", ":"))
hx = pd.DataFrame(hexrows)
R["hex"] = {"side_km": 6, "area_km2": round(1.5 * math.sqrt(3) * 36, 1), "n": int(len(hx)),
            "max_per_km2": float(hx.per_km2.max()), "median_per_km2": round(float(hx.per_km2.median()), 3),
            "n_over_1": int((hx.per_km2 >= 1).sum())}

# ---------- groups table ----------
gt = []
for g in MAPG + ["fulacht fia"]:
    x = d[d.group == g]
    gt.append(dict(group=g, n=len(x), drawn_1840=int((x.first_dep == 1).sum()), map_n=R["map_by_group"][g]["n"],
                   map_kept=R["map_by_group"][g]["share"], map_kept_adjusted=R["map_adjusted"].get(g),
                   notes_usable=int(x.notes.sum()),
                   gone_1840=R["gone_by_group_1840"].get(g, {}).get("share"), gone_1840_n=R["gone_by_group_1840"].get(g, {}).get("n"),
                   median_elev_m=round(float(x.elev_m.median()), 1)))
pd.DataFrame(gt).to_csv(os.path.join(D, "group_survival.csv"), index=False)

# ---------- the fairy premium in plain numbers ----------
R["premium_map_vs_barrow_pp"] = round((adj_map["ringfort"] - adj_map["barrow"]) * 100, 1)
R["premium_map_vs_moated_pp"] = round((adj_map["ringfort"] - adj_map["moated site"]) * 100, 1)
R["premium_map_vs_enclosure_pp"] = round((adj_map["ringfort"] - adj_map["enclosure"]) * 100, 1)
R["premium_gone_vs_enclosure_pp"] = round((adj_n["enclosure"] - adj_n["ringfort"]) * 100, 1)
R["ringfort_lost_from_map_share"] = round(1 - R["map_by_group"]["ringfort"]["share"], 4)
R["ringfort_gone_1840_n"] = R["gone_by_group_1840"]["ringfort"]["k"]

# ---------- Great Britain names ----------
gb = pd.read_csv(os.path.join(D, "gb_folk_names.csv"))
R["gb"] = {"n": int(len(gb)), "by_element": {k: int(v) for k, v in gb.element.value_counts().items()},
           "fairy_by_country": {k: int(v) for k, v in gb[gb.element == "fairy"].country.value_counts().items()},
           "fairy_hillock": int(gb.name.str.contains(r"Fairy Hillock|Fairies Hillock|Fairyfold Hillock", case=False).sum()),
           "by_type": {k: int(v) for k, v in gb.type.value_counts().items()}}
hill = gb[gb.name.str.contains(r"Fairy Hillock|Fairies Hillock|Fairyfold Hillock", case=False)]
R["gb"]["fairy_hillock_by_country"] = {k: int(v) for k, v in hill.country.value_counts().items()}
# coverage of the first-edition field for ringforts, by county
cov = d[d.group == "ringfort"].groupby("county26").first_dep.apply(lambda s: s.notna().mean()).sort_values()
R["first_field_coverage"] = {k: round(float(v), 4) for k, v in cov.items()}
R["first_field_low"] = [k for k, v in cov.items() if v < 0.1]

# ---------- compact page data ----------
mp = d[d.group.isin(["ringfort", "enclosure", "barrow", "moated site", "earthwork", "mound"])].copy()
GL = ["ringfort", "enclosure", "barrow", "moated site", "earthwork", "mound"]
CL = sorted(mp.cls.unique())
CO = sorted(mp.county.unique())
TL = sorted(mp.townland.fillna("").unique())
tli = {t: i for i, t in enumerate(TL)}
STL = {"visible": 0, "damaged": 1, "gone": 2, "": 3}


def code(v):
    return -1 if pd.isna(v) else int(v)


pts = []
for r in mp.itertuples():
    pts.append([round(r.lat, 4), round(r.lon, 4), GL.index(r.group), CL.index(r.cls), STL.get(r.status if isinstance(r.status, str) else "", 3),
                code(r.first_dep), code(r.first_labelled), code(r.latest_dep), CO.index(r.county), tli[r.townland if isinstance(r.townland, str) else ""],
                r.id, int(round(r.elev_m)), 1 if r.folk == 1 else 0])
import re  # noqa: E402
# typographic clean-up for display: en dashes to hyphens, and the trailing hyphens of SMR numbers removed
folkd = {r.id: re.sub(r"-{2,}", "", r.folk_snippet.replace("\u2013", "-").replace("\u2014", "-")) for r in fk.itertuples()}
site = {"groups": GL, "classes": CL, "counties": CO, "townlands": TL, "pts": pts, "folk": folkd,
        "hex": feats, "gb": gb[["element", "name", "local_type", "lat", "lon", "county"]].values.tolist()}
json.dump(site, open(os.path.join(W, "site_data.json"), "w"), separators=(",", ":"), ensure_ascii=False)


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if (isinstance(o, float) and math.isnan(o)) else float(o)
    return o


json.dump(clean(R), open(os.path.join(D, "results.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: R[k] for k in ["map_by_group", "map_adjusted", "gone_by_group_1840", "gone_adjusted_1840", "labelled", "labelled_gone_adjusted",
                                     "labelled_gone_adjusted_ringforts", "townland", "townland_gone_adjusted", "folk", "county_gap_gone", "county_gap_map", "hex",
                                     "premium_map_vs_barrow_pp", "premium_gone_vs_enclosure_pp", "gone_or_per100m", "gone_or_per_degree"]}, indent=1, default=str))
