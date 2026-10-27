# Fairy Forts: did fairy belief protect Ireland's ringforts?

Ireland has tens of thousands of ringforts, long known as fairy forts that it was unlucky to disturb. Short answer: not in any way the national record can see. This study sets every ringfort in the Republic of Ireland's Sites and Monuments Record against other earthworks of similar build (enclosures, barrows, moated sites, mounds) to see whether the ringforts survived better.

**Interactive version:** https://tristan-hotham.github.io/fairy-forts/

**Paper:** https://doi.org/10.5281/zenodo.23691874

By Dr Tristan Hotham, Independent researcher (ORCID 0000-0003-4931-9349).

## Headline results

- The record holds 31,431 ringforts (26,000 raths, 3,551 cashels, 1,880 unclassified) among 151,308 entries, about 0.45 per km². Sligo is the densest county (1.25 per km²).
- Of 11,555 ringforts drawn on the first OS six-inch map (c.1840), 88.6% are still drawn on the latest edition in the record (median year 1921 where dated). Barrows did just as well (88.0%), moated sites 80.6%, enclosures 70.1%. Adjusted for county, height and slope, ringforts lead barrows by 2.4 points and moated sites by 1.9, but enclosures by 19.8.
- Classes partly depend on survival (only 49.5% of "unclassified" ringforts drawn c.1840 are still on the latest map, against 91.7% of raths). Pooling ringforts and enclosures as round earthworks, 84.5% stayed on the map (adjusted 84.5%), against 86.3% for barrows and 86.6% for moated sites: no premium.
- Of ringforts drawn c.1840 with notes online, 16.3% now have no visible surface trace, against 42.4% of enclosures (adjusted 16.4% against 40.2%). Much of this gap is classification: a site needs to survive well to be called a ringfort, and 52.0% of "unclassified" ringforts have gone.
- Sites on higher ground were lost less often (odds ratio 0.75 per 100 m in the notes model).
- Only 28 of 28,410 ringfort notes mention fairies, superstition, bad luck, the púca or similar.
- Ringforts in townlands named Lis, Rath, Raheen or Caher have gone slightly less often (19.0% against 21.0%). Being named "Fort" on the 1840 map makes no difference among ringforts once county, height and slope are allowed for.
- In Great Britain, OS Open Names has 112 features named with fairy, Puck, pixie, Hob or boggart; all 20 fairy hillocks are in Scotland.

All numbers are in `data/results.json`.

## Files

- `index.html`: the interactive page (map, charts, quotes). Data are embedded, so it works as a single file.
- `header.png`: social card (1200 by 630).
- `data/sites.csv`: one row per earthwork in scope (68,000): SMR entity ID, class, group, county, townland, latitude, longitude, first and latest OS edition fields as recorded, the parsed depiction flags (`first_dep`, `first_labelled`, `latest_dep`, `latest_year`), whether usable notes exist, the note-based status (`visible`, `damaged`, `gone`) with the sentence that decided it, folklore flag and snippet, townland name element (`lis`, `rath`, `caher`), elevation (m) and slope (degrees).
- `data/county_summary.csv`: ringfort counts, density and survival measures by county.
- `data/group_survival.csv`: survival by kind of earthwork.
- `data/hex_grid.geojson`: 6 km hexagons (93.5 km²) with ringfort counts, density and survival.
- `data/folklore_notes.csv`: the 52 notes that mention fairies or related beliefs.
- `data/gb_folk_names.csv`: fairy, Puck, pixie, Hob and boggart names in OS Open Names.
- `data/validation_sample.csv`: 60 randomly drawn notes, with the rules' reading and a reading of the full note.
- `data/class_counts.csv`: every SMR monument class with its count.
- `data/county_areas.csv`: county areas (km²) used for densities, with source.
- `data/results.json`: every number used in the page, paper, blog post and collage.
- `code/`: the analysis, run in order (below). `notes_rules.py` holds the rules for reading the notes.

## How to rerun

```
python3 code/01_extract.py      # reads the SMR and the terrain tiles, writes data/sites.csv
python3 code/02_gb_names.py     # OS Open Names, writes data/gb_folk_names.csv
python3 code/03_analyse.py      # all statistics, writes results.json and the other data files
python3 code/04_build_page.py   # fills code/page_template.html to make index.html
python3 code/05_header.py       # header.png (Playwright)
```

Step 3 writes `_work/site_data.json` (embedded in the page by step 4, then safe to delete); step 1 writes `_work/outlines.json` (Natural Earth outlines used by the figures). The paper, blog figures and Reddit image are made by `release/make_figures.py`, `release/paper/build_paper.py`, `release/build_blog.py` and `reddit/collage.py`.

Inputs: the SMR open data as JSON (`ireland_smr_all.json.gz`, set its path with the `SMR` environment variable), AWS Terrain Tiles at zoom 10 as one binary file plus index, read by `code/dem.py` (from the Within Sight project; set `DEM_BIN` and `DEM_IDX`), Natural Earth 10m countries, and the OS Open Names compact table. Python 3 with numpy, pandas, statsmodels, shapely, pyproj and playwright.

## Method in brief

- **Map survival:** among sites whose first-edition field describes a depiction c.1840, the share whose latest-edition field also does. Blank or "NULL" fields are unknown. First-edition mentions in the notes are ignored, because the notes mention the old map far more often for sites that have since gone (3,080 sites).
- **Note survival:** regular-expression rules applied sentence by sentence mark a note "gone" (no visible surface trace, levelled, destroyed, removed, not visible at ground level, known only from aerial images or as a cropmark), "damaged" (partial loss) or "visible". On a fresh random sample of 60 notes the rules agreed with a full reading 54 times (4 overcounted loss, 2 missed it). Placeholder notes ("not yet uploaded") are left out.
- **Adjustment:** logistic regressions with county fixed effects, elevation and slope; adjusted shares are averaged predictions with every site set to each group.

## Known limits

- The record is a survey of what was noticed and recorded. Survival is a proxy, and classes partly depend on survival (a levelled site is less often called a ringfort).
- Association is not cause: ringforts differ from other earthworks in size, date, build and use.
- First-edition fields are almost empty for Cork, Carlow, Cavan, Kerry and Laois, and notes are mostly placeholders in some counties (Clare 60% of ringforts).
- Recording practice differs between county inventories, so county comparisons should be read with care.
- Northern Ireland is not covered.

## Sources and licences

- Sites and Monuments Record: National Monuments Service, Department of Housing, Local Government and Heritage (Archaeological Survey of Ireland), SMR open data, CC BY 4.0. https://www.archaeology.ie/
- Elevation: AWS Terrain Tiles by Mapzen/Tilezen, built from sources including SRTM, GMTED2010, ETOPO1 and national datasets. Attribution: https://github.com/tilezen/joerd/blob/master/docs/attribution.md
- Outline of Ireland: Natural Earth (public domain).
- County areas: Wikipedia, "List of Irish counties by area" (CC BY-SA 4.0), https://en.wikipedia.org/wiki/List_of_Irish_counties_by_area
- OS Open Names: Ordnance Survey, Open Government Licence v3.0. Contains OS data © Crown copyright and database right 2026.
- Base map tiles on the page: © Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS user community.

The derived data (`data/`) and the page text are released under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). The code (`code/`) is released under the MIT licence (see `LICENSE`).

## Citation

Hotham, T. (2026) *Did fairy belief protect Ireland's ringforts? Survival of ringforts and other earthworks in the Sites and Monuments Record.* Zenodo. https://doi.org/10.5281/zenodo.23691874

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
