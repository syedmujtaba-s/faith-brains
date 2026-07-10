from datetime import datetime

import sqlalchemy as sa
from pgvector.sqlalchemy import HALFVEC
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

EMBEDDING_DIM = 1024


class Base(DeclarativeBase):
    pass


class Edition(Base):
    """One imported source edition (Quran script, translation, or hadith dataset).

    `version` and `attribution` are license obligations (QuranEnc/Tanzil), not metadata trivia.
    """

    __tablename__ = "editions"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(sa.Text, unique=True)
    kind: Mapped[str] = mapped_column(sa.Text)  # quran_text | quran_translation | hadith
    name: Mapped[str] = mapped_column(sa.Text)
    language: Mapped[str | None] = mapped_column(sa.Text)
    author: Mapped[str | None] = mapped_column(sa.Text)
    source_url: Mapped[str | None] = mapped_column(sa.Text)
    license_name: Mapped[str | None] = mapped_column(sa.Text)
    attribution: Mapped[str | None] = mapped_column(sa.Text)
    version: Mapped[str | None] = mapped_column(sa.Text)
    checksum_sha256: Mapped[str | None] = mapped_column(sa.Text)
    imported_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class Surah(Base):
    __tablename__ = "surahs"

    number: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    name_arabic: Mapped[str] = mapped_column(sa.Text)
    name_english: Mapped[str] = mapped_column(sa.Text)
    name_transliterated: Mapped[str] = mapped_column(sa.Text)
    revelation_place: Mapped[str] = mapped_column(sa.Text)  # Meccan | Medinan
    revelation_order: Mapped[int | None]
    ayah_count: Mapped[int]

    verses: Mapped[list["QuranVerse"]] = relationship(back_populates="surah")


class QuranVerse(Base):
    __tablename__ = "quran_verses"
    __table_args__ = (
        sa.UniqueConstraint("surah_number", "ayah_number", name="uq_verse_surah_ayah"),
        sa.Index(
            "ix_verses_arabic_trgm",
            "text_arabic_normalized",
            postgresql_using="gin",
            postgresql_ops={"text_arabic_normalized": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    surah_number: Mapped[int] = mapped_column(sa.ForeignKey("surahs.number"))
    ayah_number: Mapped[int]
    text_uthmani: Mapped[str] = mapped_column(sa.Text)
    text_simple: Mapped[str] = mapped_column(sa.Text)
    text_arabic_normalized: Mapped[str] = mapped_column(sa.Text)
    # Tanzil prepends the basmala to ayah 1 of suras 2-114 (except 9); we split it out verbatim.
    basmala_prefix: Mapped[str | None] = mapped_column(sa.Text)
    juz: Mapped[int | None]
    hizb_quarter: Mapped[int | None]
    ruku: Mapped[int | None]
    manzil: Mapped[int | None]
    page: Mapped[int | None]
    sajda: Mapped[str | None] = mapped_column(sa.Text)  # recommended | obligatory

    surah: Mapped[Surah] = relationship(back_populates="verses")
    translations: Mapped[list["QuranTranslation"]] = relationship(back_populates="verse")


class QuranTranslation(Base):
    __tablename__ = "quran_translations"
    __table_args__ = (
        sa.UniqueConstraint("verse_id", "edition_id", name="uq_translation_verse_edition"),
        sa.Index("ix_qt_tsv", "tsv", postgresql_using="gin"),
        sa.Index(
            "ix_qt_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "halfvec_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    verse_id: Mapped[int] = mapped_column(sa.ForeignKey("quran_verses.id"))
    edition_id: Mapped[int] = mapped_column(sa.ForeignKey("editions.id"))
    # License obligation (QuranEnc): text is verbatim, never edited.
    text: Mapped[str] = mapped_column(sa.Text)
    footnotes: Mapped[str | None] = mapped_column(sa.Text)
    tsv = mapped_column(
        TSVECTOR,
        sa.Computed("to_tsvector('english', coalesce(text, ''))", persisted=True),
    )
    embedding = mapped_column(HALFVEC(EMBEDDING_DIM), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(sa.Text)

    verse: Mapped[QuranVerse] = relationship(back_populates="translations")
    edition: Mapped[Edition] = relationship()


class AskLog(Base):
    """Audit trail for /ask — quality review and abuse spotting (admin views)."""

    __tablename__ = "ask_logs"
    __table_args__ = (sa.Index("ix_ask_logs_created", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.text("now()")
    )
    question: Mapped[str] = mapped_column(sa.Text)
    category: Mapped[str | None] = mapped_column(sa.Text)
    answer: Mapped[str | None] = mapped_column(sa.Text)
    sources = mapped_column(JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"))
    provider: Mapped[str | None] = mapped_column(sa.Text)
    model: Mapped[str | None] = mapped_column(sa.Text)
    latency_ms: Mapped[int | None]
    status: Mapped[str] = mapped_column(sa.Text, server_default="ok")
    error: Mapped[str | None] = mapped_column(sa.Text)


class HadithCollection(Base):
    __tablename__ = "hadith_collections"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(sa.Text, unique=True)  # bukhari, muslim, ...
    name_english: Mapped[str] = mapped_column(sa.Text)
    name_arabic: Mapped[str | None] = mapped_column(sa.Text)
    # Canonical count for validation reporting (e.g. Bukhari 7563); dataset rows may differ.
    canonical_count: Mapped[int | None]

    records: Mapped[list["HadithRecord"]] = relationship(back_populates="collection")


class HadithRecord(Base):
    __tablename__ = "hadith_records"
    __table_args__ = (
        sa.UniqueConstraint("collection_id", "hadith_number", name="uq_hadith_collection_number"),
        sa.Index("ix_hadith_tsv", "tsv", postgresql_using="gin"),
        sa.Index(
            "ix_hadith_arabic_trgm",
            "text_arabic_normalized",
            postgresql_using="gin",
            postgresql_ops={"text_arabic_normalized": "gin_trgm_ops"},
        ),
        sa.Index(
            "ix_hadith_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "halfvec_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    collection_id: Mapped[int] = mapped_column(sa.ForeignKey("hadith_collections.id"))
    # Global reference number as string: letter suffixes ("2564a") and decimal variants exist.
    hadith_number: Mapped[str] = mapped_column(sa.Text)
    arabic_number: Mapped[str | None] = mapped_column(sa.Text)
    # Book "numbers" are strings on purpose ("introduction", "35b").
    book_number: Mapped[str | None] = mapped_column(sa.Text)
    book_name: Mapped[str | None] = mapped_column(sa.Text)
    number_in_book: Mapped[str | None] = mapped_column(sa.Text)
    text_arabic: Mapped[str | None] = mapped_column(sa.Text)
    text_arabic_normalized: Mapped[str | None] = mapped_column(sa.Text)
    text_english: Mapped[str | None] = mapped_column(sa.Text)
    # [{"name": "Al-Albani", "grade": "Sahih"}, ...] — store all graders, display primary.
    gradings = mapped_column(JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"))
    # {"in_book": "Book 67, Hadith 1", ...} — numbering is multi-scheme and shifts across editions.
    reference_schemes = mapped_column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
    tsv = mapped_column(
        TSVECTOR,
        sa.Computed("to_tsvector('english', coalesce(text_english, ''))", persisted=True),
    )
    embedding = mapped_column(HALFVEC(EMBEDDING_DIM), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(sa.Text)

    collection: Mapped[HadithCollection] = relationship(back_populates="records")
