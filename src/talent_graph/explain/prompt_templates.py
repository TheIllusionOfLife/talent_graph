"""Prompt templates for LLM-based person brief generation."""

from __future__ import annotations

import re

_TAG_RE = re.compile(r"<[^>]*>")

PROMPT_VERSION = "v1"

_SYSTEM_PROMPT = """You are an expert talent analyst. Given evidence about a researcher or engineer, \
write a concise 2-3 sentence brief explaining why they are relevant to the search context. \
Base your assessment strictly on the provided evidence — do not invent facts."""

_USER_TEMPLATE = """\
Search context: {seed_text}

Candidate: {name}
{org_line}\
Papers ({paper_count} total, {recent_count} recent):
{paper_list}
Score breakdown: semantic_similarity={semantic_similarity:.2f}, \
graph_proximity={graph_proximity:.2f}, novelty={novelty:.2f}, \
growth={growth:.2f}, evidence_quality={evidence_quality:.2f}, credibility={credibility:.2f}
Hop distance from seed: {hop_distance}

Write a 2-3 sentence brief explaining why this person is relevant to "{seed_text}"."""

_FALLBACK_TEMPLATE = """\
{seed_context}\
{name} is a researcher{org_phrase} with {paper_count} publication(s) and a relevance score of \
{score:.2f}. Their profile shows {novelty_label} citation prominence and {growth_label} recent \
publication activity, suggesting they may be a {expert_label}.\
"""


def build_brief_prompt(
    person: object,
    seed_text: str,
    hop_distance: int,
    score_breakdown: dict[str, float],
) -> tuple[str, str]:
    """Build (system_prompt, user_prompt) for person brief generation.

    Args:
        person: Person ORM object with .name, .org, .papers attributes.
        seed_text: The original search query or seed entity description.
        hop_distance: Graph distance from seed to candidate.
        score_breakdown: Dict with keys matching PersonFeatures fields.

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    papers = getattr(person, "papers", []) or []
    from datetime import datetime

    current_year = datetime.now().year
    recent_cutoff = current_year - 2
    recent_papers = [
        p
        for p in papers
        if getattr(p, "publication_year", None) and p.publication_year >= recent_cutoff
    ]

    # Truncate paper list to stay within token budget (~2K input tokens)
    top_papers = sorted(papers, key=lambda p: getattr(p, "citation_count", 0), reverse=True)[:8]
    paper_lines = "\n".join(
        f"  - {_TAG_RE.sub('', p.title).strip()} ({getattr(p, 'publication_year', '?')}, {getattr(p, 'citation_count', 0)} citations)"
        for p in top_papers
    )
    if not paper_lines:
        paper_lines = "  (none)"

    org = getattr(person, "org", None)
    safe_org_name = _TAG_RE.sub("", org.name).strip() if org else ""
    org_line = f"Affiliation: {safe_org_name}\n" if org else ""

    # Sanitize all user-visible strings: strip XML-like tags (common prompt injection vector).
    safe_seed_text = _TAG_RE.sub("", " ".join(seed_text.split()))[:500]
    safe_name = _TAG_RE.sub("", person.name).strip()

    user_prompt = _USER_TEMPLATE.format(
        seed_text=safe_seed_text,
        name=safe_name,
        org_line=org_line,
        paper_count=len(papers),
        recent_count=len(recent_papers),
        paper_list=paper_lines,
        hop_distance=hop_distance,
        **{
            k: score_breakdown.get(k, 0.0)
            for k in [
                "semantic_similarity",
                "graph_proximity",
                "novelty",
                "growth",
                "evidence_quality",
                "credibility",
            ]
        },
    )

    return _SYSTEM_PROMPT, user_prompt


def render_template_fallback(
    person: object,
    score_breakdown: dict[str, float],
    seed_text: str | None = None,
    hop_distance: int | None = None,
) -> str:
    """Render a template-based brief without LLM (offline fallback).

    Args:
        person: Person ORM object.
        score_breakdown: Dict with ranking signal scores.
        seed_text: Optional search query to include in the brief for context.
        hop_distance: Optional graph hop distance from the seed entity.

    Returns:
        Plain-text brief string.
    """
    papers = getattr(person, "papers", []) or []
    org = getattr(person, "org", None)
    org_phrase = f" affiliated with {org.name}" if org else ""

    seed_context = ""
    if seed_text:
        safe_seed = _TAG_RE.sub("", " ".join(seed_text.split()))[:200]
        hop_part = f" (hop distance: {hop_distance})" if hop_distance is not None else ""
        seed_context = f'For search "{safe_seed}"{hop_part}, '

    novelty = score_breakdown.get("novelty", 0.5)
    growth = score_breakdown.get("growth", 0.5)
    total_score = sum(score_breakdown.values()) / max(len(score_breakdown), 1)

    novelty_label = "low" if novelty < 0.4 else ("moderate" if novelty < 0.7 else "high")
    growth_label = "low" if growth < 0.4 else ("moderate" if growth < 0.7 else "strong")

    credibility = score_breakdown.get("credibility", 0.5)
    evidence = score_breakdown.get("evidence_quality", 0.5)
    if novelty >= 0.7 and evidence >= 0.5:
        expert_label = "hidden expert"
    elif growth >= 0.7:
        expert_label = "emerging researcher"
    elif credibility >= 0.7:
        expert_label = "established researcher"
    else:
        expert_label = "relevant candidate"

    return _FALLBACK_TEMPLATE.format(
        seed_context=seed_context,
        name=person.name,
        org_phrase=org_phrase,
        paper_count=len(papers),
        score=total_score,
        novelty_label=novelty_label,
        growth_label=growth_label,
        expert_label=expert_label,
    )
