"""extensions, editions, quran tables

Revision ID: 0001
Revises:
Create Date: 2026-07-09
"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import TSVECTOR

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = 1024


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "editions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.Text, nullable=False, unique=True),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("language", sa.Text),
        sa.Column("author", sa.Text),
        sa.Column("source_url", sa.Text),
        sa.Column("license_name", sa.Text),
        sa.Column("attribution", sa.Text),
        sa.Column("version", sa.Text),
        sa.Column("checksum_sha256", sa.Text),
        sa.Column("imported_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "surahs",
        sa.Column("number", sa.Integer, primary_key=True, autoincrement=False),
        sa.Column("name_arabic", sa.Text, nullable=False),
        sa.Column("name_english", sa.Text, nullable=False),
        sa.Column("name_transliterated", sa.Text, nullable=False),
        sa.Column("revelation_place", sa.Text, nullable=False),
        sa.Column("revelation_order", sa.Integer),
        sa.Column("ayah_count", sa.Integer, nullable=False),
    )

    op.create_table(
        "quran_verses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("surah_number", sa.Integer, sa.ForeignKey("surahs.number"), nullable=False),
        sa.Column("ayah_number", sa.Integer, nullable=False),
        sa.Column("text_uthmani", sa.Text, nullable=False),
        sa.Column("text_simple", sa.Text, nullable=False),
        sa.Column("text_arabic_normalized", sa.Text, nullable=False),
        sa.Column("basmala_prefix", sa.Text),
        sa.Column("juz", sa.Integer),
        sa.Column("hizb_quarter", sa.Integer),
        sa.Column("ruku", sa.Integer),
        sa.Column("manzil", sa.Integer),
        sa.Column("page", sa.Integer),
        sa.Column("sajda", sa.Text),
        sa.UniqueConstraint("surah_number", "ayah_number", name="uq_verse_surah_ayah"),
    )

    op.create_table(
        "quran_translations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("verse_id", sa.Integer, sa.ForeignKey("quran_verses.id"), nullable=False),
        sa.Column("edition_id", sa.Integer, sa.ForeignKey("editions.id"), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("footnotes", sa.Text),
        sa.Column(
            "tsv",
            TSVECTOR,
            sa.Computed("to_tsvector('english', coalesce(text, ''))", persisted=True),
        ),
        sa.Column("embedding", Vector(EMBEDDING_DIM)),
        sa.Column("embedding_model", sa.Text),
        sa.UniqueConstraint("verse_id", "edition_id", name="uq_translation_verse_edition"),
    )


def downgrade() -> None:
    op.drop_table("quran_translations")
    op.drop_table("quran_verses")
    op.drop_table("surahs")
    op.drop_table("editions")
