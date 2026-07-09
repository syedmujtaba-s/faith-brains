"""search indexes: GIN tsvector, trigram, HNSW vector, FK btrees

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-09
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Full-text
    op.create_index("ix_qt_tsv", "quran_translations", ["tsv"], postgresql_using="gin")
    op.create_index("ix_hadith_tsv", "hadith_records", ["tsv"], postgresql_using="gin")

    # Arabic substring match on normalized text
    op.create_index(
        "ix_verses_arabic_trgm",
        "quran_verses",
        ["text_arabic_normalized"],
        postgresql_using="gin",
        postgresql_ops={"text_arabic_normalized": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_hadith_arabic_trgm",
        "hadith_records",
        ["text_arabic_normalized"],
        postgresql_using="gin",
        postgresql_ops={"text_arabic_normalized": "gin_trgm_ops"},
    )

    # Vector ANN (cosine). HNSW builds fine on empty tables and stays valid as rows arrive.
    op.create_index(
        "ix_qt_embedding_hnsw",
        "quran_translations",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        "ix_hadith_embedding_hnsw",
        "hadith_records",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    # FK lookup paths
    op.create_index("ix_verses_surah", "quran_verses", ["surah_number"])
    op.create_index("ix_qt_verse", "quran_translations", ["verse_id"])
    op.create_index("ix_qt_edition", "quran_translations", ["edition_id"])
    op.create_index("ix_hadith_collection", "hadith_records", ["collection_id"])


def downgrade() -> None:
    for name, table in [
        ("ix_hadith_collection", "hadith_records"),
        ("ix_qt_edition", "quran_translations"),
        ("ix_qt_verse", "quran_translations"),
        ("ix_verses_surah", "quran_verses"),
        ("ix_hadith_embedding_hnsw", "hadith_records"),
        ("ix_qt_embedding_hnsw", "quran_translations"),
        ("ix_hadith_arabic_trgm", "hadith_records"),
        ("ix_verses_arabic_trgm", "quran_verses"),
        ("ix_hadith_tsv", "hadith_records"),
        ("ix_qt_tsv", "quran_translations"),
    ]:
        op.drop_index(name, table_name=table)
