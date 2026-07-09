"""Parse direct scripture references out of a user query.

A query like "2:255", "2 255", "2:1-5", or "baqarah 255" should short-circuit search and
resolve to exact verses. Numeric parsing is pure; surah-name resolution needs the DB and
happens in the service layer.
"""

import re
from dataclasses import dataclass

_NUMERIC_REF = re.compile(r"^\s*(\d{1,3})\s*[:. ]\s*(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?\s*$")
_NAME_REF = re.compile(
    r"^\s*(?:surah?|sura|سورة)?\s*([a-zA-Z' \-]{3,30}?)\s+(\d{1,3})(?:\s*[-–]\s*(\d{1,3}))?\s*$"
)


@dataclass(frozen=True)
class QuranRef:
    surah: int | None  # None when only a name was given (resolve in service)
    surah_name: str | None
    ayah_start: int
    ayah_end: int | None


# Famous "named verses": mentioning one anywhere in a query ("Which verse is Ayat
# al-Kursi?") resolves directly, since no lexical/vector signal reliably maps the
# nickname to the verse text. Keys are letters-only, space-joined forms.
_NAMED_VERSES: dict[str, tuple[int, int]] = {
    "ayat al kursi": (2, 255),
    "ayatul kursi": (2, 255),
    "ayat ul kursi": (2, 255),
    "ayah al kursi": (2, 255),
    "throne verse": (2, 255),
    "verse of the throne": (2, 255),
    "verse of light": (24, 35),
    "light verse": (24, 35),
    "ayat an nur": (24, 35),
    "ayat al nur": (24, 35),
    "verse of debt": (2, 282),
    "debt verse": (2, 282),
    "ayat ad dayn": (2, 282),
    "ayat al dayn": (2, 282),
}


def _named_verse(query: str) -> QuranRef | None:
    padded = " " + " ".join(re.findall(r"[a-z]+", query.lower())) + " "
    for name, (surah, ayah) in _NAMED_VERSES.items():
        if f" {name} " in padded:
            return QuranRef(surah=surah, surah_name=None, ayah_start=ayah, ayah_end=None)
    return None


def parse_quran_reference(query: str) -> QuranRef | None:
    m = _NUMERIC_REF.match(query)
    if m:
        surah, start, end = int(m.group(1)), int(m.group(2)), m.group(3)
        if not 1 <= surah <= 114:
            return None
        return QuranRef(
            surah=surah, surah_name=None, ayah_start=start, ayah_end=int(end) if end else None
        )
    m = _NAME_REF.match(query)
    if m:
        name = m.group(1).strip().lower()
        start, end = int(m.group(2)), m.group(3)
        # Reject obvious non-name phrases ("verses about 5" etc.) — require a wordish token
        if not re.search(r"[a-z]{3}", name):
            return None
        return QuranRef(
            surah=None, surah_name=name, ayah_start=start, ayah_end=int(end) if end else None
        )
    return _named_verse(query)


def _norm_surah_name(name: str) -> str:
    """Fold a surah name for transliteration-tolerant comparison.

    Lowercase, letters only, collapse doubled letters, drop trailing 'h':
    "Al-Baqara" -> "albaqara", "baqarah" -> "baqara", "Yaa-Seen" -> "yasen".
    """
    letters = re.sub(r"[^a-z]", "", name.lower())
    collapsed = re.sub(r"(.)\1+", r"\1", letters)
    return collapsed.removesuffix("h")


def surah_name_matches(query_name: str, *candidates: str) -> bool:
    """True if the query plausibly names this surah (either side contains the other).

    Containment absorbs the Arabic article ("rahman" vs "Ar-Rahmaan") and partial
    forms; the caller must still enforce uniqueness across all 114 surahs. The reverse
    direction (name inside query) needs a length floor or tiny names like "Man" (76)
    and "Nas" (114) false-match inside longer queries.
    """
    q = _norm_surah_name(query_name)
    if len(q) < 3:
        return False
    for candidate in candidates:
        c = _norm_surah_name(candidate)
        if c and (q in c or (c in q and len(c) >= 5)):
            return True
    return False


_HADITH_REF = re.compile(
    r"^\s*(bukhari|muslim|abudawud|abu\s*dawud|tirmidhi|nasai|ibnmajah|ibn\s*majah|malik|nawawi|qudsi)"
    r"\s*[:# ]\s*(\d{1,5}[a-z]?)\s*$",
    re.IGNORECASE,
)

_COLLECTION_ALIASES = {
    "abu dawud": "abudawud",
    "ibn majah": "ibnmajah",
}


@dataclass(frozen=True)
class HadithRef:
    collection_key: str
    number: str


def parse_hadith_reference(query: str) -> HadithRef | None:
    m = _HADITH_REF.match(query)
    if not m:
        return None
    raw = re.sub(r"\s+", " ", m.group(1).strip().lower())
    key = _COLLECTION_ALIASES.get(raw, raw.replace(" ", ""))
    return HadithRef(collection_key=key, number=m.group(2).lower())
