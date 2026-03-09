"""Add repo_contributors join table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "repo_contributors",
        sa.Column("repo_id", sa.String(36), sa.ForeignKey("repos.id"), primary_key=True),
        sa.Column("person_id", sa.String(36), sa.ForeignKey("persons.id"), primary_key=True),
        sa.Column("contributions", sa.Integer, default=0),
    )


def downgrade() -> None:
    op.drop_table("repo_contributors")
