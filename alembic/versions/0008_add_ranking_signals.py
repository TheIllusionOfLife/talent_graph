"""add ranking_signals table for Learning to Rank

Revision ID: 0008_ranking_signals
Revises: 0007_saved_searches
Create Date: 2026-03-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008_ranking_signals"
down_revision = "0007_saved_searches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ranking_signals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("person_id", sa.String(36), sa.ForeignKey("persons.id"), nullable=False),
        sa.Column("query", sa.Text, nullable=True),
        sa.Column(
            "action",
            sa.String(32),
            sa.CheckConstraint(
                "action IN ('save', 'discard', 'shortlist', 'remove')",
                name="ck_ranking_signals_action",
            ),
            nullable=False,
        ),
        sa.Column("context", JSONB, nullable=True),
        sa.Column("owner_key", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ranking_signals_person_id", "ranking_signals", ["person_id"])
    op.create_index("ix_ranking_signals_query", "ranking_signals", ["query"])
    op.create_index("ix_ranking_signals_owner_key", "ranking_signals", ["owner_key"])


def downgrade() -> None:
    op.drop_index("ix_ranking_signals_owner_key", table_name="ranking_signals")
    op.drop_index("ix_ranking_signals_query", table_name="ranking_signals")
    op.drop_index("ix_ranking_signals_person_id", table_name="ranking_signals")
    op.drop_table("ranking_signals")
