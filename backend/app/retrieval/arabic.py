"""Arabic text normalization for search.

Displayed text is always the verbatim source text; normalization exists only in the
separate *_normalized columns and on incoming queries, so license-mandated verbatim
display is never affected.
"""

import re
import unicodedata

# Tashkeel + Quranic annotation marks + superscript alef etc.
_DIACRITICS = re.compile(
    "["
    "ً-ٟ"  # tanween, fatha/damma/kasra, shadda, sukun, small marks
    "ٰ"  # superscript alef
    "ۖ-ۭ"  # Quranic annotation signs (waqf marks, small high letters)
    "࣓-ࣿ"  # extended Arabic small marks
    "]"
)
_TATWEEL = "ـ"

_ALEF_VARIANTS = str.maketrans(
    {
        "آ": "ا",  # آ
        "أ": "ا",  # أ
        "إ": "ا",  # إ
        "ٱ": "ا",  # ٱ (wasla)
    }
)

_LETTER_FOLDS = str.maketrans(
    {
        "ى": "ي",  # ى -> ي
        "ة": "ه",  # ة -> ه
    }
)

_ARABIC_CHARS = re.compile(r"[؀-ۿݐ-ݿࢠ-ࣿ]")
_WS = re.compile(r"\s+")


def normalize_arabic(text: str) -> str:
    """Fold Arabic text to a search-normalized form (strip diacritics, unify letter variants)."""
    text = unicodedata.normalize("NFC", text)
    text = _DIACRITICS.sub("", text)
    text = text.replace(_TATWEEL, "")
    text = text.translate(_ALEF_VARIANTS).translate(_LETTER_FOLDS)
    return _WS.sub(" ", text).strip()


def contains_arabic(text: str) -> bool:
    return bool(_ARABIC_CHARS.search(text))
