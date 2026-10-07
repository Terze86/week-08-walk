import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from pydantic import ValidationError

from app.core.config import Settings
from app.core.db import get_engine
from app.models import Base


def test_production_refuses_dev_auth_and_local_files() -> None:
    with pytest.raises(ValidationError, match="OIDC"):
        Settings(environment="production", auth_mode="dev")
    with pytest.raises(ValidationError, match="S3"):
        Settings(
            environment="production",
            auth_mode="oidc",
            oidc_issuer="i",
            oidc_audience="a",
            oidc_jwks_url="u",
            file_store="local",
        )


def test_migrations_match_models() -> None:
    with get_engine().connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []
