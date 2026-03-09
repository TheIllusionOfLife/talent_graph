"""Add index on entity_links.status for pending-queue queries.

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_entity_links_status", "entity_links", ["status"])


def downgrade() -> None:
    op.drop_index("ix_entity_links_status", table_name="entity_links")
