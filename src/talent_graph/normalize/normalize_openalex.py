"""OpenAlex API response → common schema normalizer."""

from talent_graph.normalize.common_schema import (
    AuthorPosition,
    ConceptRecord,
    OrgRecord,
    PaperRecord,
    PersonRecord,
)


def _strip_openalex_prefix(url: str | None) -> str | None:
    """'https://openalex.org/W123' → 'W123'"""
    if not url:
        return None
    return url.split("/")[-1] if url.startswith("http") else url


def _reconstruct_abstract(inverted_index: dict[str, list[int]]) -> str | None:
    """Reconstruct plaintext from OpenAlex abstract_inverted_index format."""
    if not inverted_index:
        return None
    word_positions: list[tuple[int, str]] = [
        (pos, word) for word, positions in inverted_index.items() for pos in positions
    ]
    word_positions.sort()
    return " ".join(word for _, word in word_positions)


def _parse_institution(raw: dict) -> OrgRecord:
    return OrgRecord(
        name=raw.get("display_name", ""),
        openalex_institution_id=_strip_openalex_prefix(raw.get("id")),
        country_code=raw.get("country_code"),
        type=raw.get("type"),
    )


def _parse_authorship(authorship: dict, position: int) -> AuthorPosition:
    author_raw = authorship.get("author", {})
    institutions = authorship.get("institutions") or []
    org = _parse_institution(institutions[0]) if institutions else None

    person = PersonRecord(
        name=author_raw.get("display_name", ""),
        openalex_author_id=_strip_openalex_prefix(author_raw.get("id")),
        orcid=author_raw.get("orcid"),
        org=org,
    )
    return AuthorPosition(
        person=person,
        position=position,
        is_corresponding=authorship.get("is_corresponding", False),
    )


def normalize_work(raw: dict) -> PaperRecord:
    """Normalize a single OpenAlex Works API response object."""
    authorships = raw.get("authorships") or []
    authors: list[AuthorPosition] = []
    for i, authorship in enumerate(authorships):
        # Use list index (1-based) to preserve stable ordering across all positions.
        # OpenAlex "first"/"middle"/"last" labels are not numerically stable for
        # papers with many middle authors.
        position = i + 1
        authors.append(_parse_authorship(authorship, position))

    concepts: list[ConceptRecord] = []
    for c in raw.get("concepts") or []:
        concept_id = _strip_openalex_prefix(c.get("id"))
        if concept_id:
            concepts.append(
                ConceptRecord(
                    openalex_concept_id=concept_id,
                    name=c.get("display_name", ""),
                    level=c.get("level", 0),
                    score=float(c.get("score", 0.0)),
                )
            )

    abstract_raw = raw.get("abstract_inverted_index")
    abstract = _reconstruct_abstract(abstract_raw) if abstract_raw else None

    return PaperRecord(
        title=raw.get("title", ""),
        openalex_work_id=_strip_openalex_prefix(raw.get("id")),  # None when ID is absent
        publication_year=raw.get("publication_year"),
        citation_count=raw.get("cited_by_count", 0),
        doi=raw.get("doi"),
        abstract=abstract,
        authors=authors,
        concepts=concepts,
    )
