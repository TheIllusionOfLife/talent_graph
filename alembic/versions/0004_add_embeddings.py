"""Add vector embedding column to persons table.

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable pgvector extension (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add embedding column (384-dim, BAAI/bge-small-en-v1.5)
    op.add_column("persons", sa.Column("embedding", Vector(384), nullable=True))

    # IVFFlat index for cosine similarity ANN queries.
    # lists=100 is appropriate for up to ~1M rows; tune after bulk seeding.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_persons_embedding_ivfflat "
        "ON persons USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_persons_embedding_ivfflat")
    op.drop_column("persons", "embedding")
