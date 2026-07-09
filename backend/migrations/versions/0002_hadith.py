"""hadith collections and records

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-09
"""
import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

EMBEDDING_DIM = 1024


def upgrade() -> None:
    op.create_table(
        "hadith_collections",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.Text, nullable=False, unique=True),
        sa.Column("name_english", sa.Text, nullable=False),
        sa.Column("name_arabic", sa.Text),
        sa.Column("canonical_count", sa.Integer),
    )

    op.create_table(
        "hadith_records",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "collection_id", sa.Integer, sa.ForeignKey("hadith_collections.id"), nullable=False
        ),
        sa.Column("hadith_number", sa.Text, nullable=False),
        sa.Column("arabic_number", sa.Text),
        sa.Column("book_number", sa.Text),
        sa.Column("book_name", sa.Text),
        sa.Column("number_in_book", sa.Text),
        sa.Column("text_arabic", sa.Text),
        sa.Column("text_arabic_normalized", sa.Text),
        sa.Column("text_english", sa.Text),
        sa.Column("gradings", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "reference_schemes", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "tsv",
            TSVECTOR,
            sa.Computed("to_tsvector('english', coalesce(text_english, ''))", persisted=True),
        ),
        sa.Column("embedding", Vector(EMBEDDING_DIM)),
        sa.Column("embedding_model", sa.Text),
        sa.UniqueConstraint("collection_id", "hadith_number", name="uq_hadith_collection_number"),
    )


def downgrade() -> None:
    op.drop_table("hadith_records")
    op.drop_table("hadith_collections")
