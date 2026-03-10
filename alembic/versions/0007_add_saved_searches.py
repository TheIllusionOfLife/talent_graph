"""add saved_searches table

Revision ID: 0007_saved_searches
Revises: 0006
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0007_saved_searches"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saved_searches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("owner_key", sa.String(256), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("query", sa.Text, nullable=False),
        sa.Column("filters", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("now()"), nullable=False),
        sa.Column("last_run_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_saved_searches_owner_key", "saved_searches", ["owner_key"])


def downgrade() -> None:
    op.drop_index("ix_saved_searches_owner_key", table_name="saved_searches")
    op.drop_table("saved_searches")
