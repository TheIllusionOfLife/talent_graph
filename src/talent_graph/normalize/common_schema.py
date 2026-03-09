"""Canonical internal schema — source-agnostic data transfer objects."""

from dataclasses import dataclass, field


@dataclass
class ConceptRecord:
    openalex_concept_id: str
    name: str
    level: int
    score: float = 0.0  # relevance to the paper


@dataclass
class OrgRecord:
    name: str
    openalex_institution_id: str | None = None
    country_code: str | None = None
    type: str | None = None


@dataclass
class PersonRecord:
    name: str
    openalex_author_id: str | None = None
    github_login: str | None = None
    orcid: str | None = None
    email: str | None = None
    homepage: str | None = None
    org: OrgRecord | None = None
    # Assigned during entity resolution; None until resolved
    canonical_person_id: str | None = None


@dataclass
class AuthorPosition:
    person: PersonRecord
    position: int  # 1-based
    is_corresponding: bool = False


@dataclass
class PaperRecord:
    title: str
    openalex_work_id: str
    publication_year: int | None = None
    citation_count: int = 0
    doi: str | None = None
    abstract: str | None = None
    authors: list[AuthorPosition] = field(default_factory=list)
    concepts: list[ConceptRecord] = field(default_factory=list)


@dataclass
class RepoRecord:
    full_name: str  # "owner/repo"
    description: str | None = None
    language: str | None = None
    stars: int = 0
    forks: int = 0
    topics: list[str] = field(default_factory=list)
    github_repo_id: int | None = None
    owner_login: str | None = None  # person or org github login
    owner_type: str | None = None  # "User" | "Organization"
    contributor_logins: list[str] = field(default_factory=list)
