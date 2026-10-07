"""Import every model module so Base.metadata is complete (Alembic, tests)."""

from app.core import access, audit, documents, files, ids, jobs  # noqa: F401
from app.core.db import APPEND_ONLY_TABLES, Base  # noqa: F401
from app.modules.identity import models as identity_models  # noqa: F401
