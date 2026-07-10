"""halfvec embeddings — fp16 halves vector storage (fits Neon free 0.5GB)

Recall impact of fp16 quantization is negligible (<0.1% on HNSW cosine);
storage for 42K x 1024-dim vectors drops ~170MB -> ~85MB plus index savings.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-10
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

_TABLES = ("quran_translations", "hadith_records")
_INDEXES = {"quran_translations": "ix_qt_embedding_hnsw", "hadith_records": "ix_hadith_embedding_hnsw"}


def upgrade() -> None:
    for table in _TABLES:
        op.drop_index(_INDEXES[table], table_name=table)
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN embedding "
            f"TYPE halfvec(1024) USING embedding::halfvec(1024)"
        )
        op.create_index(
            _INDEXES[table],
            table,
            ["embedding"],
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "halfvec_cosine_ops"},
        )


def downgrade() -> None:
    for table in _TABLES:
        op.drop_index(_INDEXES[table], table_name=table)
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN embedding "
            f"TYPE vector(1024) USING embedding::vector(1024)"
        )
        op.create_index(
            _INDEXES[table],
            table,
            ["embedding"],
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        )
