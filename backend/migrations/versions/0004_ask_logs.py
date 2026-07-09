"""ask_logs — Q&A audit trail for admin review

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-09
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ask_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("category", sa.Text),
        sa.Column("answer", sa.Text),
        sa.Column("sources", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("provider", sa.Text),
        sa.Column("model", sa.Text),
        sa.Column("latency_ms", sa.Integer),
        sa.Column("status", sa.Text, nullable=False, server_default="ok"),
        sa.Column("error", sa.Text),
    )
    op.create_index("ix_ask_logs_created", "ask_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ask_logs_created", table_name="ask_logs")
    op.drop_table("ask_logs")
