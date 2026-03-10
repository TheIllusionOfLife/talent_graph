"""IsolationForest-based hidden expert detection.

Scores each person on how anomalous their profile is relative to the corpus.
High score (→ 1.0) means the person is an outlier — potentially a hidden expert
with unusual combination of low citations, high activity, and cross-source evidence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import structlog
from sklearn.ensemble import IsolationForest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from talent_graph.storage.models import Person
from talent_graph.storage.postgres import get_db_session

log = structlog.get_logger()

_CONTAMINATION = 0.1
_DEFAULT_RANDOM_STATE = 42
_RECENT_YEAR_WINDOW = 2


@dataclass
class PersonFeatureRow:
    """Extracted feature vector for one person."""

    person_id: str
    citation_count: int
    paper_count: int
    recent_paper_count: int
    source_count: int
    years_active: int


class HiddenExpertDetector:
    """Fits an IsolationForest on log1p-scaled person features and produces [0,1] scores."""

    def __init__(
        self,
        contamination: float = _CONTAMINATION,
        random_state: int = _DEFAULT_RANDOM_STATE,
    ) -> None:
        self._contamination = contamination
        self._random_state = random_state
        self._model: IsolationForest | None = None

    def fit(self, rows: list[PersonFeatureRow]) -> HiddenExpertDetector:
        """Train the IsolationForest on the provided feature rows."""
        X = self._to_matrix(rows)
        self._model = IsolationForest(
            contamination=self._contamination,
            random_state=self._random_state,
        )
        self._model.fit(X)
        return self

    def scores(self, rows: list[PersonFeatureRow]) -> dict[str, float | None]:
        """Return {person_id: score | None} for each row.

        Persons with paper_count < 1 get None (insufficient data).
        Scores are normalized to [0, 1]; higher = more anomalous (more "hidden").
        """
        if self._model is None:
            raise RuntimeError("Call fit() before scores()")

        result: dict[str, float | None] = {}

        # Separate rows with and without papers
        valid = [r for r in rows if r.paper_count >= 1]
        for r in rows:
            if r.paper_count < 1:
                result[r.person_id] = None

        if not valid:
            return result

        X = self._to_matrix(valid)
        raw = self._model.decision_function(X)

        # decision_function: more negative → more anomalous
        # Normalize to [0, 1]: higher score = more anomalous
        min_val = float(raw.min())
        max_val = float(raw.max())
        denom = max_val - min_val if (max_val - min_val) > 1e-9 else 1.0

        for row, raw_score in zip(valid, raw, strict=True):
            normalized = 1.0 - (float(raw_score) - min_val) / denom
            result[row.person_id] = round(max(0.0, min(1.0, normalized)), 6)

        return result

    @staticmethod
    def _to_matrix(rows: list[PersonFeatureRow]) -> np.ndarray:
        """Convert rows to log1p-scaled feature matrix."""
        return np.array(
            [
                [
                    math.log1p(r.citation_count),
                    math.log1p(r.paper_count),
                    math.log1p(r.recent_paper_count),
                    math.log1p(r.source_count),
                    math.log1p(r.years_active),
                ]
                for r in rows
            ],
            dtype=float,
        )


async def _fetch_feature_rows(current_year: int) -> list[PersonFeatureRow]:
    """Load all persons with their papers and extract feature rows."""
    async with get_db_session() as session:
        result = await session.execute(select(Person).options(selectinload(Person.papers)))
        persons = result.scalars().all()

    rows = []
    for person in persons:
        papers = person.papers or []
        citation_count = sum(p.citation_count for p in papers)
        paper_count = len(papers)
        recent_cutoff = current_year - _RECENT_YEAR_WINDOW
        recent_paper_count = sum(
            1 for p in papers if p.publication_year and p.publication_year >= recent_cutoff
        )
        source_count = sum(
            1 for v in [person.openalex_author_id, person.github_login, person.orcid] if v
        )
        years = [p.publication_year for p in papers if p.publication_year]
        years_active = max(1, current_year - min(years) + 1) if years else 0

        rows.append(
            PersonFeatureRow(
                person_id=person.id,
                citation_count=citation_count,
                paper_count=paper_count,
                recent_paper_count=recent_paper_count,
                source_count=source_count,
                years_active=years_active,
            )
        )
    return rows


async def _persist_scores(scores: dict[str, float | None]) -> None:
    """Write hidden_expert_score back to each Person row."""
    from sqlalchemy import update

    async with get_db_session() as session:
        for person_id, score in scores.items():
            await session.execute(
                update(Person).where(Person.id == person_id).values(hidden_expert_score=score)
            )


async def compute_hidden_expert_scores(current_year: int | None = None) -> int:
    """Full pipeline: fetch → fit → score → persist.

    Returns the number of persons scored (None-scored persons are counted too).
    """
    from datetime import datetime

    year = current_year or datetime.now().year

    rows = await _fetch_feature_rows(year)
    if not rows:
        log.info("hidden_expert.skip", reason="no persons in database")
        return 0

    detector = HiddenExpertDetector()
    detector.fit(rows)
    scores = detector.scores(rows)

    await _persist_scores(scores)
    log.info("hidden_expert.done", scored=len(scores))
    return len(scores)
