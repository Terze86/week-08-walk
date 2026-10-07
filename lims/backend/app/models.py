"""Import every model module so Base.metadata is complete (Alembic, tests)."""

from app.core import access, audit, documents, files, ids, jobs  # noqa: F401
from app.core.db import APPEND_ONLY_TABLES, Base  # noqa: F401
from app.modules.cases import models as cases_models  # noqa: F401
from app.modules.custody import models as custody_models  # noqa: F401
from app.modules.identity import models as identity_models  # noqa: F401
from app.modules.items import models as items_models  # noqa: F401
from app.modules.receipt import models as receipt_models  # noqa: F401
from app.modules.reference import models as reference_models  # noqa: F401
