"""GET /graph/ego/{node_type}/{node_id} — force-graph-compatible ego subgraph."""

from typing import Any, Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from starlette.requests import Request

from talent_graph.api.deps import require_api_key
from talent_graph.api.limiter import limiter
from talent_graph.graph.neo4j_client import run_query
from talent_graph.storage.models import Concept, Org, Paper, Person, Repo
from talent_graph.storage.postgres import get_db_session

log = structlog.get_logger()
router = APIRouter(prefix="/graph", tags=["graph"])

# ── Node config: maps URL node_type → Neo4j label + Postgres model ────────

_NODE_CONFIG: dict[str, dict[str, Any]] = {
    "person": {"label": "Person", "id_field": "person_id", "model": Person, "key_attr": "id"},
    "paper": {
        "label": "Paper",
        "id_field": "openalex_work_id",
        "model": Paper,
        "key_attr": "openalex_work_id",
    },
    "concept": {
        "label": "Concept",
        "id_field": "openalex_concept_id",
        "model": Concept,
        "key_attr": "openalex_concept_id",
    },
    "org": {
        "label": "Org",
        "id_field": "openalex_institution_id",
        "model": Org,
        "key_attr": "openalex_institution_id",
    },
    "repo": {"label": "Repo", "id_field": "full_name", "model": Repo, "key_attr": "full_name"},
}

# ── Response models ───────────────────────────────────────────────────────


class GraphNode(BaseModel):
    id: str  # compound: "person__abc123"
    type: str  # "Person", "Paper", etc.
    label: str
    metadata: dict[str, Any]


class GraphLink(BaseModel):
    source: str  # GraphNode.id
    target: str  # GraphNode.id
    type: str  # "AUTHORED", "ABOUT", etc.


class EgoGraphResponse(BaseModel):
    center_id: str
    nodes: list[GraphNode]
    links: list[GraphLink]
    truncated: bool


# ── Cypher templates (one per hop value for query plan caching) ───────────

_EGO_QUERY_TEMPLATE = """
MATCH (seed:{label} {{{id_field}: $seed_key}})
MATCH path = (seed)-[*1..{hops}]-(neighbor)
WITH seed, collect(DISTINCT neighbor) AS raw_neighbors
WITH seed, raw_neighbors[0..$node_limit] AS neighbors, size(raw_neighbors) > $node_limit AS truncated
WITH seed, neighbors + [seed] AS all_nodes, truncated
UNWIND all_nodes AS a
MATCH (a)-[r]->(b)
WHERE b IN all_nodes
WITH all_nodes, truncated, collect(DISTINCT r) AS rels
UNWIND all_nodes AS n
WITH DISTINCT n, truncated, rels
RETURN
  collect(DISTINCT {{
    type: labels(n)[0],
    node_key: CASE labels(n)[0]
      WHEN 'Person' THEN n.person_id  WHEN 'Paper' THEN n.openalex_work_id
      WHEN 'Concept' THEN n.openalex_concept_id
      WHEN 'Org' THEN n.openalex_institution_id  WHEN 'Repo' THEN n.full_name
    END,
    label: CASE labels(n)[0]
      WHEN 'Person' THEN n.name  WHEN 'Paper' THEN n.title
      WHEN 'Concept' THEN n.name  WHEN 'Org' THEN n.name  WHEN 'Repo' THEN n.full_name
    END,
    props: properties(n)
  }}) AS nodes,
  [r IN rels | {{
    source_type: labels(startNode(r))[0],
    source_key: CASE labels(startNode(r))[0]
      WHEN 'Person' THEN startNode(r).person_id  WHEN 'Paper' THEN startNode(r).openalex_work_id
      WHEN 'Concept' THEN startNode(r).openalex_concept_id
      WHEN 'Org' THEN startNode(r).openalex_institution_id  WHEN 'Repo' THEN startNode(r).full_name
    END,
    target_type: labels(endNode(r))[0],
    target_key: CASE labels(endNode(r))[0]
      WHEN 'Person' THEN endNode(r).person_id  WHEN 'Paper' THEN endNode(r).openalex_work_id
      WHEN 'Concept' THEN endNode(r).openalex_concept_id
      WHEN 'Org' THEN endNode(r).openalex_institution_id  WHEN 'Repo' THEN endNode(r).full_name
    END,
    rel_type: type(r)
  }}] AS links,
  truncated
"""


# ── Helpers (exported for unit tests) ─────────────────────────────────────


def _build_compound_id(node_type: str, natural_key: str) -> str:
    """Build compound ID: {type_lower}__{natural_key}."""
    return f"{node_type.lower()}__{natural_key}"


def _canonicalize_links(links: list[dict[str, str]]) -> list[dict[str, str]]:
    """Deduplicate bidirectional edges (e.g. COAUTHORED_WITH A→B and B→A)."""
    seen: set[tuple[str, str, str]] = set()
    result: list[dict[str, str]] = []
    for link in links:
        key = (
            min(link["source"], link["target"]),
            max(link["source"], link["target"]),
            link["type"],
        )
        if key not in seen:
            seen.add(key)
            result.append(link)
    return result


def _transform_results(raw: dict[str, Any], center_id: str) -> EgoGraphResponse:
    """Transform Neo4j raw result into EgoGraphResponse."""
    nodes: list[GraphNode] = []
    for n in raw.get("nodes", []):
        if n.get("node_key") is None:
            continue
        compound_id = _build_compound_id(n["type"], n["node_key"])
        nodes.append(
            GraphNode(
                id=compound_id,
                type=n["type"],
                label=n.get("label") or str(n["node_key"]),
                metadata=n.get("props", {}),
            )
        )

    # Build compound links
    raw_links: list[dict[str, str]] = []
    for link in raw.get("links", []):
        if link.get("source_key") is None or link.get("target_key") is None:
            continue
        raw_links.append(
            {
                "source": _build_compound_id(link["source_type"], link["source_key"]),
                "target": _build_compound_id(link["target_type"], link["target_key"]),
                "type": link["rel_type"],
            }
        )

    canon_links = _canonicalize_links(raw_links)
    graph_links = [GraphLink(**lk) for lk in canon_links]

    return EgoGraphResponse(
        center_id=center_id,
        nodes=nodes,
        links=graph_links,
        truncated=bool(raw.get("truncated", False)),
    )


# ── Route ─────────────────────────────────────────────────────────────────


@router.get(
    "/ego/{node_type}/{node_id}",
    response_model=EgoGraphResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit("30/minute")
async def get_ego_graph(
    request: Request,
    node_type: Literal["person", "paper", "repo", "concept", "org"],
    node_id: str,
    hops: int = Query(default=2, ge=1, le=3),
    node_limit: int = Query(default=150, ge=1, le=300),
) -> EgoGraphResponse:
    """Return force-graph-compatible subgraph centered on a node."""
    cfg = _NODE_CONFIG[node_type]

    # 1. Resolve Postgres ID → Neo4j natural key
    async with get_db_session() as session:
        row = await session.get(cfg["model"], node_id)

    if row is None:
        raise HTTPException(status_code=404, detail=f"{cfg['label']} not found")

    seed_key = getattr(row, cfg["key_attr"])
    if seed_key is None:
        raise HTTPException(status_code=404, detail=f"{cfg['label']} has no graph key")

    center_id = _build_compound_id(cfg["label"], seed_key)

    # 2. Build Cypher query (hops is validated 1-3, safe to interpolate)
    cypher = _EGO_QUERY_TEMPLATE.format(
        label=cfg["label"],
        id_field=cfg["id_field"],
        hops=hops,
    )

    # 3. Execute single Neo4j read query
    try:
        rows = await run_query(cypher, {"seed_key": seed_key, "node_limit": node_limit})
    except Exception as exc:
        log.warning("graph.ego.neo4j_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="Graph database unavailable") from exc

    if not rows:
        return EgoGraphResponse(center_id=center_id, nodes=[], links=[], truncated=False)

    # 4. Transform and return
    return _transform_results(rows[0], center_id)
