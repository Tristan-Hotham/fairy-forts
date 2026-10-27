"""Step 2. Fairy-type place names in Great Britain from OS Open Names (OGL v3).

Counts named features whose name contains the word fairy (fairies, faery), Puck, pixie (pixy, pixey,
piskie), Hob (as a word: Hob, Hobs, Hob's, plus hobgoblin and hobthrush; Hobb and Hobbs are left out as they are mostly surnames) or boggart (boggard).
This counts the words on the map; it makes no claim about where any name comes from. Puck and Hob in
particular can occur in names with other origins, such as surnames.

Input:  /home/claude/hist/osnames_gb.tsv (compact OS Open Names, read in place)
Output: data/gb_folk_names.csv
"""
import os
import re

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OSN = os.environ.get("OSN", "/home/claude/hist/osnames_gb.tsv")
PATS = {
    "fairy": r"\bfair(?:y|ies|ie's|ies')|\bfaery|\bfairyfold|\bfairyrow",
    "puck": r"\bpuck(?:'?s)?\b|\bpuckstool|\bpuckpit|\bpuckwell|\bpuckhill|\bpuckhole|\bpuck ?well|\bpucks?hole",
    "pixie": r"\bpix(?:ie|y|ey|ies)|\bpisk(?:ie|y|ies)",
    "hob": r"\bhob(?:'?s)?\b|\bhobgoblin|\bhobthrush|\bhobhole",
    "boggart": r"\bbogg(?:art|ard)",
}
d = pd.read_csv(OSN, sep="\t", dtype=str, keep_default_na=False)
rows = []
for k, p in PATS.items():
    rx = re.compile(p, re.I)
    m = d[d.name1.str.contains(rx) | d.name2.str.contains(rx)]
    for _, r in m.iterrows():
        rows.append(dict(element=k, name=r["name1"], name2=r["name2"], type=r["type"], local_type=r["local_type"],
                         lat=float(r["lat"]), lon=float(r["lon"]), county=r["county"], country=r["country"]))
out = pd.DataFrame(rows).drop_duplicates(subset=["name", "lat", "lon"])
out.to_csv(os.path.join(ROOT, "data", "gb_folk_names.csv"), index=False)
print(out.groupby(["element", "country"]).size())
