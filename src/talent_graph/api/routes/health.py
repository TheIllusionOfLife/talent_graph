"""Health check endpoint — no auth required."""

import sqlalchemy
from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from starlette.requests import Request  # noqa: TC002

from talent_graph.api.limiter import limiter
from talent_graph.graph.neo4j_client import verify_connectivity
from talent_graph.storage.postgres import get_db_session

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    postgres: str
    neo4j: str


@router.get("/health", response_model=HealthResponse)
@limiter.limit("60/minute")
async def health(request: Request, response: Response) -> HealthResponse:
    # Postgres
    try:
        async with get_db_session() as session:
            await session.execute(sqlalchemy.text("SELECT 1"))
        pg_status = "ok"
    except Exception:
        pg_status = "error"

    # Neo4j
    neo4j_status = "ok" if await verify_connectivity() else "error"

    overall = "ok" if pg_status == "ok" and neo4j_status == "ok" else "degraded"
    if overall != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(status=overall, postgres=pg_status, neo4j=neo4j_status)
