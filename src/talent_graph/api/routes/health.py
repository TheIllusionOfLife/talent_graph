"""Health check endpoint — no auth required."""

from fastapi import APIRouter
from pydantic import BaseModel

from talent_graph.graph.neo4j_client import verify_connectivity
from talent_graph.storage.postgres import get_db_session

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    postgres: str
    neo4j: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    # Postgres
    try:
        async with get_db_session() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
        pg_status = "ok"
    except Exception:
        pg_status = "error"

    # Neo4j
    neo4j_status = "ok" if await verify_connectivity() else "error"

    overall = "ok" if pg_status == "ok" and neo4j_status == "ok" else "degraded"
    return HealthResponse(status=overall, postgres=pg_status, neo4j=neo4j_status)
