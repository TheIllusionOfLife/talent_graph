"""Shared pytest fixtures for all test tiers."""

import os

# Force test env vars before any app imports — direct assignment ensures tests
# are isolated from the caller's shell environment (setdefault would allow
# accidental targeting of non-test services).
os.environ["API_KEY"] = "test-key"
os.environ["LOG_FORMAT"] = "text"
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://talent_graph:talent_graph@localhost:5432/talent_graph"
)
os.environ["NEO4J_URI"] = "bolt://localhost:7687"
os.environ["NEO4J_USER"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "talent_graph"
