"""ASGI entry point for production deployment."""

from talent_graph.api.main import create_app

app = create_app()
