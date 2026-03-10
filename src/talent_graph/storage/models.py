"""SQLAlchemy ORM models for PostgreSQL."""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Person(Base):
    __tablename__ = "persons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # ULID
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    openalex_author_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    github_login: Mapped[str | None] = mapped_column(String(256), unique=True, nullable=True)
    orcid: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(512), nullable=True)
    homepage: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    org_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("orgs.id"), nullable=True)
    raw_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    hidden_expert_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    org: Mapped["Org | None"] = relationship("Org", back_populates="members")
    papers: Mapped[list["Paper"]] = relationship(
        "Paper", secondary="paper_authors", back_populates="authors"
    )


class Org(Base):
    __tablename__ = "orgs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    openalex_institution_id: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True
    )
    github_org_login: Mapped[str | None] = mapped_column(String(256), unique=True, nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    members: Mapped[list["Person"]] = relationship("Person", back_populates="org")


class Concept(Base):
    __tablename__ = "concepts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    openalex_concept_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    wikidata_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    openalex_work_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    doi: Mapped[str | None] = mapped_column(String(256), nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    citation_count: Mapped[int] = mapped_column(Integer, default=0)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    concepts: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    raw_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    authors: Mapped[list["Person"]] = relationship(
        "Person", secondary="paper_authors", back_populates="papers"
    )


class PaperAuthor(Base):
    __tablename__ = "paper_authors"
    # No __table_args__ — composite PK (paper_id, person_id) already enforces uniqueness

    paper_id: Mapped[str] = mapped_column(String(36), ForeignKey("papers.id"), primary_key=True)
    person_id: Mapped[str] = mapped_column(String(36), ForeignKey("persons.id"), primary_key=True)
    author_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_corresponding: Mapped[bool] = mapped_column(Boolean, default=False)


class Repo(Base):
    __tablename__ = "repos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    github_repo_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    forks: Mapped[int] = mapped_column(Integer, default=0)
    topics: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    owner_person_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("persons.id"), nullable=True
    )
    owner_org_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("orgs.id"), nullable=True
    )
    raw_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RepoContributor(Base):
    """Join table: persons who contributed to a repo (ordered by contribution count)."""

    __tablename__ = "repo_contributors"

    repo_id: Mapped[str] = mapped_column(String(36), ForeignKey("repos.id"), primary_key=True)
    person_id: Mapped[str] = mapped_column(String(36), ForeignKey("persons.id"), primary_key=True)
    contributions: Mapped[int] = mapped_column(Integer, default=0)


class EntityLink(Base):
    """Cross-source entity resolution candidates awaiting review."""

    __tablename__ = "entity_links"
    __table_args__ = (
        UniqueConstraint("person_id_a", "person_id_b"),
        # Enforce canonical ordering so (A,B) and (B,A) cannot both exist.
        # Entity resolution code must sort IDs before inserting.
        CheckConstraint("person_id_a < person_id_b", name="ck_entity_links_ordered_ids"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    person_id_a: Mapped[str] = mapped_column(String(36), ForeignKey("persons.id"), nullable=False)
    person_id_b: Mapped[str] = mapped_column(String(36), ForeignKey("persons.id"), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(String(64), nullable=False)  # "deterministic" | "heuristic"
    status: Mapped[str] = mapped_column(
        String(32), default="pending"
    )  # "pending" | "merged" | "rejected"
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Shortlist(Base):
    """A named collection of candidate persons."""

    __tablename__ = "shortlists"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # ULID
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # owner_key enables per-user filtering in Sprint 5 without a migration
    owner_key: Mapped[str] = mapped_column(String(256), nullable=False, default="default")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["ShortlistItem"]] = relationship(
        "ShortlistItem", back_populates="shortlist", cascade="all, delete-orphan"
    )


class PrestigeOrg(Base):
    """Configurable prestige organisation list for credibility scoring."""

    __tablename__ = "prestige_orgs"

    name: Mapped[str] = mapped_column(Text, primary_key=True)  # stored lowercase
    tier: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 = top, 2 = high, …


class ShortlistItem(Base):
    """A person pinned to a shortlist with optional note and ordering."""

    __tablename__ = "shortlist_items"
    # No __table_args__ needed: composite PK (shortlist_id, person_id) already enforces uniqueness.

    shortlist_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("shortlists.id", ondelete="CASCADE"), primary_key=True
    )
    person_id: Mapped[str] = mapped_column(String(36), ForeignKey("persons.id"), primary_key=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    added_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    shortlist: Mapped["Shortlist"] = relationship("Shortlist", back_populates="items")
    person: Mapped["Person"] = relationship("Person")


class SavedSearch(Base):
    """A persisted search query with optional filters, owned by an API key."""

    __tablename__ = "saved_searches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # ULID
    owner_key: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON blob: {"mode": "standard", "limit": 20, "entity_type": "concept", ...}
    filters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
