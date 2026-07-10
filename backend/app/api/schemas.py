"""Pydantic response schemas for the public API."""

from typing import Literal

from pydantic import BaseModel, Field


class EditionOut(BaseModel):
    key: str
    kind: str
    name: str
    language: str | None
    author: str | None
    source_url: str | None
    license_name: str | None
    attribution: str | None
    version: str | None

    model_config = {"from_attributes": True}


class SurahOut(BaseModel):
    number: int
    name_arabic: str
    name_english: str
    name_transliterated: str
    revelation_place: str
    revelation_order: int | None
    ayah_count: int

    model_config = {"from_attributes": True}


class TranslationOut(BaseModel):
    edition: str
    text: str
    footnotes: str | None


class VerseOut(BaseModel):
    surah: int
    ayah: int
    reference: str
    text_uthmani: str
    text_simple: str
    basmala_prefix: str | None
    juz: int | None
    page: int | None
    sajda: str | None
    translations: list[TranslationOut]


class SurahDetailOut(BaseModel):
    surah: SurahOut
    offset: int = 0
    limit: int = 0  # 0 = unpaginated (all verses); surah.ayah_count is the total
    verses: list[VerseOut]


class HadithCollectionOut(BaseModel):
    key: str
    name_english: str
    name_arabic: str | None
    hadith_count: int


class GradingOut(BaseModel):
    name: str | None
    grade: str | None


class HadithListOut(BaseModel):
    collection: str
    collection_name: str
    total: int
    offset: int
    limit: int
    items: list["HadithOut"]


class HadithOut(BaseModel):
    collection: str
    collection_name: str
    number: str
    book_number: str | None
    book_name: str | None
    number_in_book: str | None
    text_arabic: str | None
    text_english: str | None
    gradings: list[GradingOut]
    reference_schemes: dict


class SearchResultOut(BaseModel):
    """Discriminated by `type`; quran and hadith hits carry different fields, so this
    stays permissive and mirrors the service dicts."""

    type: str
    score: float
    signals: list[str]
    reference: str
    # quran fields
    surah: int | None = None
    ayah: int | None = None
    surah_name: str | None = None
    surah_name_arabic: str | None = None
    arabic: str | None = None
    translation: str | None = None
    translation_edition: str | None = None
    juz: int | None = None
    page: int | None = None
    # hadith fields
    collection: str | None = None
    collection_name: str | None = None
    number: str | None = None
    book_number: str | None = None
    book_name: str | None = None
    english: str | None = None
    gradings: list[GradingOut] | None = None


class SearchResponse(BaseModel):
    query: str
    scope: str
    mode: str
    signals_used: list[str]
    results: list[SearchResultOut]


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    scope: Literal["all", "quran", "hadith"] = "all"


class AskResponse(BaseModel):
    question: str
    category: Literal["educational", "fatwa_seeking", "sensitive_crisis", "out_of_scope"]
    answer: str
    sources: list[SearchResultOut]
    disclaimer: str


class AskLogOut(BaseModel):
    id: int
    created_at: str
    question: str
    category: str | None
    answer: str | None
    provider: str | None
    model: str | None
    latency_ms: int | None
    status: str
    error: str | None


class AskLogListOut(BaseModel):
    total: int
    items: list[AskLogOut]


class TafsirOut(BaseModel):
    source_key: str
    source_name: str
    language: str
    text: str


class SavedItemIn(BaseModel):
    kind: Literal["quran", "hadith"]
    reference: str = Field(min_length=1, max_length=100)


class SavedItemOut(BaseModel):
    kind: str
    reference: str


class PathSummaryOut(BaseModel):
    key: str
    title: str
    description: str
    step_count: int
    completed_count: int


class PathStepOut(BaseModel):
    key: str
    title: str
    kind: str
    reference: str
    arabic: str | None
    text: str | None
    grading: str | None
    completed: bool


class PathDetailOut(BaseModel):
    key: str
    title: str
    description: str
    steps: list[PathStepOut]


class PathProgressOut(BaseModel):
    path_key: str
    completed: list[str]
    step_count: int


class AdminStatsOut(BaseModel):
    verses: int
    hadiths: int
    quran_embeddings: int
    hadith_embeddings: int
    asks_total: int
    asks_by_category: dict[str, int]
    asks_errored: int
    avg_latency_ms: float | None
