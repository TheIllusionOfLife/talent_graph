"""Shared pytest fixtures for all test tiers."""

import os

# Set test env vars before any app imports
os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("LOG_FORMAT", "text")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://talent_graph:talent_graph@localhost:5432/talent_graph",
)
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "talent_graph")
