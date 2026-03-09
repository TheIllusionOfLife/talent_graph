"""Initial schema: persons, orgs, papers, concepts, repos, entity_links.

Revision ID: 0001
Revises:
Create Date: 2026-03-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orgs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("openalex_institution_id", sa.String(64), unique=True, nullable=True),
        sa.Column("github_org_login", sa.String(256), unique=True, nullable=True),
        sa.Column("country_code", sa.String(8), nullable=True),
        sa.Column("type", sa.String(64), nullable=True),
        sa.Column("raw_metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "persons",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("openalex_author_id", sa.String(64), unique=True, nullable=True),
        sa.Column("github_login", sa.String(256), unique=True, nullable=True),
        sa.Column("orcid", sa.String(64), unique=True, nullable=True),
        sa.Column("email", sa.String(512), nullable=True),
        sa.Column("homepage", sa.String(1024), nullable=True),
        sa.Column("org_id", sa.String(36), sa.ForeignKey("orgs.id"), nullable=True),
        sa.Column("raw_metadata", postgresql.JSONB, nullable=True),
        sa.Column("hidden_expert_score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    # Note: openalex_author_id and github_login already have indexes from unique=True constraints

    op.create_table(
        "concepts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("openalex_concept_id", sa.String(64), unique=True, nullable=True),
        sa.Column("wikidata_id", sa.String(64), nullable=True),
        sa.Column("level", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "papers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("openalex_work_id", sa.String(64), unique=True, nullable=True),
        sa.Column("doi", sa.String(256), nullable=True),
        sa.Column("publication_year", sa.Integer, nullable=True),
        sa.Column("citation_count", sa.Integer, default=0),
        sa.Column("abstract", sa.Text, nullable=True),
        sa.Column("concepts", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("raw_metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    # Note: openalex_work_id already has an index from unique=True constraint
    op.create_index("ix_papers_publication_year", "papers", ["publication_year"])

    op.create_table(
        "paper_authors",
        sa.Column("paper_id", sa.String(36), sa.ForeignKey("papers.id"), primary_key=True),
        sa.Column("person_id", sa.String(36), sa.ForeignKey("persons.id"), primary_key=True),
        sa.Column("author_position", sa.Integer, nullable=True),
        sa.Column("is_corresponding", sa.Boolean, default=False),
        # UniqueConstraint omitted — composite PK (paper_id, person_id) already enforces uniqueness
    )

    op.create_table(
        "repos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("full_name", sa.String(512), unique=True, nullable=False),
        sa.Column("github_repo_id", sa.Integer, unique=True, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("language", sa.String(128), nullable=True),
        sa.Column("stars", sa.Integer, default=0),
        sa.Column("forks", sa.Integer, default=0),
        sa.Column("topics", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("owner_person_id", sa.String(36), sa.ForeignKey("persons.id"), nullable=True),
        sa.Column("owner_org_id", sa.String(36), sa.ForeignKey("orgs.id"), nullable=True),
        sa.Column("raw_metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "entity_links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("person_id_a", sa.String(36), sa.ForeignKey("persons.id"), nullable=False),
        sa.Column("person_id_b", sa.String(36), sa.ForeignKey("persons.id"), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("method", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), default="pending"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("person_id_a", "person_id_b"),
        # Canonical ordering prevents (A,B) and (B,A) from coexisting as duplicates.
        sa.CheckConstraint("person_id_a < person_id_b", name="ck_entity_links_ordered_ids"),
    )


def downgrade() -> None:
    op.drop_table("entity_links")
    op.drop_table("repos")
    op.drop_table("paper_authors")
    op.drop_table("papers")
    op.drop_table("concepts")
    op.drop_table("persons")
    op.drop_table("orgs")
