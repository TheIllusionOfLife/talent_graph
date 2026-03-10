"""Add shortlists and shortlist_items tables.

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shortlists",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_key", sa.String(256), nullable=False, server_default="default"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    # Index for future Sprint 5 per-user filtering
    op.create_index("ix_shortlists_owner_key", "shortlists", ["owner_key"])

    op.create_table(
        "shortlist_items",
        sa.Column(
            "shortlist_id",
            sa.String(36),
            sa.ForeignKey("shortlists.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("person_id", sa.String(36), sa.ForeignKey("persons.id"), primary_key=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "added_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # No UniqueConstraint needed: composite PK already enforces uniqueness.
    )


def downgrade() -> None:
    op.drop_table("shortlist_items")
    op.drop_index("ix_shortlists_owner_key", table_name="shortlists")
    op.drop_table("shortlists")
