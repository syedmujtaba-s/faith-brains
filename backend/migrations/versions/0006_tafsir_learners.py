"""tafsir corpus + anonymous learner sessions (saved items, path progress)

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-11
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tafsirs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("verse_id", sa.Integer, sa.ForeignKey("quran_verses.id"), nullable=False),
        sa.Column("source_key", sa.Text, nullable=False),
        sa.Column("source_name", sa.Text, nullable=False),
        sa.Column("language", sa.Text, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.UniqueConstraint("verse_id", "source_key", name="uq_tafsir_verse_source"),
    )
    op.create_index("ix_tafsir_verse", "tafsirs", ["verse_id"])

    op.create_table(
        "learners",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("session_id", sa.Text, nullable=False, unique=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "saved_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("learner_id", sa.Integer, sa.ForeignKey("learners.id"), nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("reference", sa.Text, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.UniqueConstraint("learner_id", "kind", "reference", name="uq_saved_learner_ref"),
    )

    op.create_table(
        "path_progress",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("learner_id", sa.Integer, sa.ForeignKey("learners.id"), nullable=False),
        sa.Column("path_key", sa.Text, nullable=False),
        sa.Column("step_key", sa.Text, nullable=False),
        sa.Column(
            "completed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.UniqueConstraint("learner_id", "path_key", "step_key", name="uq_progress_step"),
    )


def downgrade() -> None:
    op.drop_table("path_progress")
    op.drop_table("saved_items")
    op.drop_table("learners")
    op.drop_index("ix_tafsir_verse", table_name="tafsirs")
    op.drop_table("tafsirs")
