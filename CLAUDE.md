# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**talent_graph** is a Talent Discovery platform that uses knowledge graphs, embeddings, and LLM-powered explanations to find exceptional people who don't appear in traditional keyword/resume searches. It ingests public data (OpenAlex papers, GitHub repos) into a graph structure, ranks candidates by multiple signals, and explains why each candidate is relevant.

This is an application of the broader "Graph Discovery Engine" concept, initially scoped to Talent Discovery (finding hidden experts, emerging researchers).

## Status

Pre-implementation. Only design documents exist:
- `graph_discovery_engine_foundational_vision.md` — Product vision, use cases, market, roadmap
- `talent_graph_detailed_design.md` — Detailed technical design (architecture, schemas, APIs, algorithms)

## Planned Tech Stack

- **Backend**: Python + FastAPI
- **Graph DB**: Neo4j Community Edition
- **Relational DB**: PostgreSQL
- **Vector Store**: pgvector
- **Embeddings**: sentence-transformers (`BAAI/bge-small-en-v1.5` or `all-MiniLM-L6-v2`)
- **LLM**: Small OSS model + optional external API (for explanation generation)
- **ETL**: Python scripts + cron/Prefect
- **Frontend**: Next.js or React

## Architecture (5 Layers)

```
Data Sources (OpenAlex, GitHub)
  → Ingestion/ETL (fetch, normalize, entity resolution, graph transform)
    → Storage (Postgres, Neo4j, pgvector, raw JSON files)
      → Intelligence (graph traversal, ranking, anomaly detection, clustering, explanation)
        → Application (FastAPI REST API)
          → UI (Next.js)
```

## Planned Package Structure

```
talent_graph/
├── api/            # FastAPI routes and schemas
├── config/
├── ingestion/      # openalex_client, github_client, jobs
├── normalize/      # Source-specific normalizers + common schema
├── entity_resolution/  # Cross-source person/org matching
├── graph/          # Neo4j client, graph_builder, Cypher queries
├── embeddings/     # Person/Paper/Repo/Concept embedding generation
├── features/       # Feature engineering for ranking
├── ranking/        # Multi-signal candidate scoring
├── anomaly/        # Hidden expert detection (IsolationForest)
├── explain/        # LLM-powered explanation generation
├── storage/        # Postgres, vector_store, raw_store clients
├── tests/
└── scripts/
```

## Key Design Decisions

- **Facts vs inferences are strictly separated** — AI-inferred edges (SIMILAR_TO, LIKELY_EXPERT_IN) carry `source: "inferred"` and are stored apart from observed data
- **Graph visualization is secondary** — ranked list + explanation is the primary UX; graph is a supporting view
- **Hidden expert ≠ absolute quality** — anomaly scores flag candidates for deeper exploration, not definitive ranking
- **Entity resolution is gradual** — deterministic matches auto-merge; heuristic matches go to review queue
- **Ranking is a weighted linear combination** of: semantic_similarity (0.30), graph_proximity (0.20), novelty (0.15), growth (0.15), evidence_quality (0.10), credibility (0.10)
- **Three discovery modes**: standard (balanced), hidden (novelty/evidence/anomaly weighted), emerging (growth/recency weighted)

## Graph Schema (Neo4j)

**Nodes**: Person, Paper, Repo, Concept, Artifact, Org

**Key relationships**:
- `(Person)-[:AUTHORED]->(Paper)`
- `(Person)-[:CONTRIBUTED_TO]->(Repo)`
- `(Person)-[:AFFILIATED_WITH]->(Org)`
- `(Paper|Repo|Artifact)-[:ABOUT]->(Concept)`
- `(Person)-[:COAUTHORED_WITH]->(Person)`
- `(Person)-[:SIMILAR_TO]->(Person)` — inferred
- `(Person)-[:LIKELY_EXPERT_IN]->(Concept)` — inferred

## Development Commands

Not yet established. When implementation begins, use:
- `uv` for Python package/venv management
- `ruff` for formatting and linting
- `bun` for frontend package management
