"""Tests for production secrets guard — fail-fast when defaults are used."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from talent_graph.config.settings import Settings


def _make_settings(**overrides: str) -> Settings:
    """Build a Settings instance with sensible test defaults + overrides."""
    defaults: dict[str, str] = {
        "database_url": "postgresql+asyncpg://x:x@localhost/x",
        "neo4j_uri": "bolt://localhost:7687",
        "neo4j_user": "neo4j",
        "neo4j_password": "test",
        "api_key": "change-me-in-production",
        "app_secret": "change-me-in-production",
        "environment": "development",
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


class TestSecretsGuard:
    """Lifespan should RuntimeError in production with default secrets."""

    @pytest.mark.asyncio
    async def test_production_default_api_key_raises(self) -> None:
        """RuntimeError when ENVIRONMENT=production and API_KEY is default."""
        settings = _make_settings(environment="production")

        with (
            patch("talent_graph.api.main.get_settings", return_value=settings),
            patch("talent_graph.api.main.run_write_query", new_callable=AsyncMock),
            patch(
                "talent_graph.api.main.init_prestige_names",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch("talent_graph.api.main.close_driver", new_callable=AsyncMock),
            pytest.raises(RuntimeError, match="default.*production"),
        ):
            from talent_graph.api.main import create_app

            app = create_app()
            # Trigger lifespan
            async with app.router.lifespan_context(app):
                pass  # pragma: no cover

    @pytest.mark.asyncio
    async def test_production_default_app_secret_raises(self) -> None:
        """RuntimeError when ENVIRONMENT=production and APP_SECRET is default."""
        settings = _make_settings(
            environment="production",
            api_key="real-key",
        )

        with (
            patch("talent_graph.api.main.get_settings", return_value=settings),
            patch("talent_graph.api.main.run_write_query", new_callable=AsyncMock),
            patch(
                "talent_graph.api.main.init_prestige_names",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch("talent_graph.api.main.close_driver", new_callable=AsyncMock),
            pytest.raises(RuntimeError, match="default.*production"),
        ):
            from talent_graph.api.main import create_app

            app = create_app()
            async with app.router.lifespan_context(app):
                pass  # pragma: no cover

    @pytest.mark.asyncio
    async def test_production_real_secrets_ok(self) -> None:
        """No error when production has real secrets."""
        settings = _make_settings(
            environment="production",
            api_key="real-key",
            app_secret="real-secret",
        )

        with (
            patch("talent_graph.api.main.get_settings", return_value=settings),
            patch("talent_graph.api.main.run_write_query", new_callable=AsyncMock),
            patch(
                "talent_graph.api.main.init_prestige_names",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch("talent_graph.api.main.close_driver", new_callable=AsyncMock),
        ):
            from talent_graph.api.main import create_app

            app = create_app()
            async with app.router.lifespan_context(app):
                pass  # should not raise

    @pytest.mark.asyncio
    async def test_development_default_secrets_warns(self) -> None:
        """Development mode warns but does not raise."""
        settings = _make_settings(environment="development")
        mock_log = MagicMock()

        with (
            patch("talent_graph.api.main.get_settings", return_value=settings),
            patch("talent_graph.api.main.structlog.get_logger", return_value=mock_log),
            patch("talent_graph.api.main.run_write_query", new_callable=AsyncMock),
            patch(
                "talent_graph.api.main.init_prestige_names",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch("talent_graph.api.main.close_driver", new_callable=AsyncMock),
        ):
            from talent_graph.api.main import create_app

            app = create_app()
            async with app.router.lifespan_context(app):
                pass  # should not raise

        warning_events = [call.args[0] for call in mock_log.warning.call_args_list]
        assert any("insecure_default" in ev for ev in warning_events)
