"""Rules for reading the SMR WEB_NOTES text. Shared by 01_extract.py and the checks.

status():
  'gone'    the notes say the monument as a whole has no visible surface trace
            (levelled, destroyed, removed, not visible at ground level, known only
            from aerial images or old maps).
  'damaged' the notes mention levelling, destruction or removal of part of it,
            but no whole-site loss.
  'visible' no such wording.
  None      no usable notes (placeholder or empty).
"""
import re

PLACEHOLDER = "has not been uploaded"

GONE = [
    r"no (?:visible |definite |obvious |clear )?(?:surface |above[- ]ground )?(?:trace|remains|evidence)s?\b(?! of (?:an? |the )?(?:entrance|fosse|ditch|bank|internal|souterrain|hut|house|wall|structure|features?|division))",
    r"not (?:visible|evident|discernible|identifiable|apparent|traceable|recognisable) (?:at|on the) ground(?: level)?",
    r"not visible at ground level",
    r"no longer (?:visible|extant|survives?|exists?|in existence|evident|discernible|traceable)",
    r"(?:has|have) (?:since |now |all |also )?been (?:completely |totally |entirely |largely |almost completely |virtually |all but )?(?:levell?ed|destroyed|removed|bulldozed|ploughed out|quarried away|built over|obliterated)",
    r"(?:was|were) (?:completely |totally |entirely |largely |almost completely |virtually )?(?:levell?ed|destroyed|removed|bulldozed|ploughed out|obliterated|quarried away)(?! (?:at|in part|to [NSEW]))",
    r"(?:site|monument|ringfort|rath|fort|enclosure|cashel) (?:is |now )?(?:completely |totally |entirely )?(?:levell?ed|destroyed|removed)",
    r"(?:completely|totally|entirely|fully) (?:levell?ed|destroyed|removed|obliterated)",
    r"levell?ed (?:in|c\.|around|about|during|some|many|several|for|by|\d)",
    r"(?:only|now) (?:visible|survives?|known|identified|evident|recognisable|discernible) (?:as (?:an? )?(?:crop|soil|parch)[- ]?marks?|(?:on|from|in) (?:aerial|satellite|ortho|google|digital|lidar|cartographic|the os|os maps))",
    r"(?:survives|visible) only as (?:an? )?(?:crop|soil|parch)[- ]?mark",
    r"known only from (?:aerial|cartographic|the os|os|map|photograph|satellite|google|lidar|local)",
    r"\b(?:the )?site of (?:an? |the )?(?:ringfort|rath|fort|enclosure|cashel|souterrain|circular)",
    r"no visible surface",
    r"^\W*(?:the |a |an )?(?:crop|soil|parch)[- ]?marks? (?:of|shows?)\b",
    r"\b(?:shows?|as (?:the|a)) (?:the |a )?(?:crop|soil|parch)[- ]?marks? of",
    r"not (?:now )?visible (?:now )?at ground level",
    r"(?:prior to|before) (?:its |the )?(?:removal|destruction|levell?ing)",
    r"visible (?:only )?as (?:an? )?(?:crop|soil|parch)[- ]?mark",
    r"^\W*(?:now )?(?:levell?ed|destroyed|removed|demolished|bulldozed|quarried away)\b",
    r"(?:built|housing estate|house|houses) (?:has been |was |were )?(?:built|constructed|erected) (?:on|over) (?:the )?(?:site|it)",
]
PARTIAL_CUE = r"\b(?:part|partly|partially|portion|section|segment|stretch|half|sector|quadrant|interior|bank at|fosse at|at [NSEW]{1,3}\b|from [NSEW]{1,3}\b|to [NSEW]{1,3}\b|elsewhere|of (?:the )?(?:enclosure|site|monument|rath|fort) (?:to|at|on|in) )"
DAMAGE = r"levell?ed|destroyed|removed|bulldozed|ploughed out|quarried|truncated|damaged|disturbed"

FEATS = r"(?:entrance|fosse|ditch|bank|causeway|internal|interior|souterrain|hut|house|wall|structure|feature|gap|counterscarp|revetment|facing|division|annex|outer|inner|second|third|rampart|chamber|terrace|platform|field|stone|kerb|mound|lintel|scarp|chapel|church|building|graveyard|burial|grave|cross|well|cist|cairn|kiln|road|track|trackway|bawn|castle|tower)"
FEAT_AFTER = re.compile(r"^\s*(?:of|for)\s+(?:an?\s+|the\s+|any\s+)?(?:\w+\s+){0,2}" + FEATS, re.I)
FEAT_BEFORE = re.compile(FEATS + r"s?", re.I)
SITES = r"(?:site|monument|ringfort|rath|fort|enclosure|cashel|it|whole|entire|remains)"
FIRST_NOUN = re.compile(r"\b(?:" + FEATS + "|" + SITES + r")s?\b", re.I)
GONE_RE = [re.compile(p, re.I) for p in GONE]
PART_RE = re.compile(PARTIAL_CUE, re.I)
DAM_RE = re.compile(DAMAGE, re.I)
SENT_SPLIT = re.compile(r"(?<=[.;!?])\s+|\n+")


def usable(notes):
    return bool(notes and notes.strip()) and PLACEHOLDER not in notes


def status(notes):
    if not usable(notes):
        return None, ""
    sents = [s for s in SENT_SPLIT.split(notes) if s.strip()]
    for s in sents:
        for rx in GONE_RE:
            m = rx.search(s)
            if not m:
                continue
            # a sentence that also names a part ("bank at N levelled") is partial, unless it says no trace
            nt = re.search(r"no (?:visible |definite )?(?:surface |above[- ]ground )?trace|not visible at ground level|site of|only as|known only|no longer", m.group(0), re.I)
            if PART_RE.search(s) and not nt:
                continue
            after = s[m.end():m.end() + 45]
            before = s[max(0, m.start() - 70):m.start()]
            if FEAT_AFTER.match(after):
                continue
            first = FIRST_NOUN.search(before)
            if first and FEAT_BEFORE.fullmatch(first.group(0)):
                continue
            return "gone", s.strip()[:300]
    for s in sents:
        if DAM_RE.search(s):
            return "damaged", s.strip()[:300]
    return "visible", ""


FOLK = re.compile(r"\bfair(?:y|ies)\b|\bs[ií]dhe?\b|\bsidh\b|tSidhe|superstiti|\bunlucky\b|bad luck|pis(?:h)?og|pis[eé]og|\bpooka\b|\bp[uú]ca\b|\bphuca\b|liosach[aá]n|\bghost\b|haunted", re.I)


def folk(notes):
    if not usable(notes):
        return None
    m = FOLK.search(notes)
    if not m:
        return ""
    a = max(0, m.start() - 400); b = min(len(notes), m.end() + 400)
    return notes[a:b].replace("\n", " ").strip()
