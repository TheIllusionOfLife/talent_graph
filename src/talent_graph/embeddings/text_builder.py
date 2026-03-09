"""Build text strings for embedding from person/query data."""


def build_person_text(
    name: str,
    org_name: str | None = None,
    concepts: list[str] | None = None,
    paper_titles: list[str] | None = None,
) -> str:
    """Concatenate person fields into a single embedding-ready string.

    Caps paper titles at 10 to keep the embedding focused on the person's
    primary research areas rather than a long CV tail.
    """
    parts: list[str] = [name]

    if org_name:
        parts.append(org_name)

    if concepts:
        parts.append(" ".join(concepts))

    if paper_titles:
        # Deduplicate while preserving order, then cap at 10
        seen: set[str] = set()
        unique: list[str] = []
        for t in paper_titles:
            if t not in seen:
                seen.add(t)
                unique.append(t)
        parts.append(" ".join(unique[:10]))

    return " ".join(parts)


def build_query_text(query: str) -> str:
    """Normalize a free-text search query for embedding."""
    return query.strip()
