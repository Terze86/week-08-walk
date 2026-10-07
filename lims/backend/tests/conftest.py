import json
import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

os.environ.setdefault(
    "LIMS_DATABASE_URL", "postgresql+psycopg://lims:lims@localhost:5432/lims_test"
)
os.environ["LIMS_ENVIRONMENT"] = "test"
os.environ["LIMS_AUTH_MODE"] = "dev"
os.environ["LIMS_FILE_STORE"] = "local"

from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from alembic import command  # noqa: E402
from app.core.db import get_db, get_engine  # noqa: E402
from app.core.files import LocalFileStore  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.identity import service as identity  # noqa: E402
from app.modules.identity.models import Role, User  # noqa: E402

BACKEND_ROOT = Path(__file__).resolve().parents[1]


# --- URS traceability -------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--urs-report",
        default=None,
        help="Write a JSON file mapping URS IDs (docs/URS.md) to test outcomes.",
    )


_urs_results: list[dict[str, object]] = []


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[None]) -> Iterator[None]:
    outcome = yield
    report = outcome.get_result()  # type: ignore[attr-defined]
    if report.when != "call" and not (report.when == "setup" and report.failed):
        return
    ids = [i for m in item.iter_markers("urs") for i in m.args]
    if ids:
        _urs_results.append({"test": item.nodeid, "urs": ids, "outcome": report.outcome})


def pytest_sessionfinish(session: pytest.Session) -> None:
    path = session.config.getoption("--urs-report")
    if path:
        Path(path).write_text(json.dumps(_urs_results, indent=2))


# --- Database ---------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")


@pytest.fixture
def db() -> Iterator[Session]:
    """A session inside an outer transaction that is always rolled back, so
    append-only tables never need cleaning between tests."""
    connection = get_engine().connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture
def file_store(tmp_path: Path) -> LocalFileStore:
    return LocalFileStore(tmp_path / "files")


# --- Users ------------------------------------------------------------------

MakeUser = Callable[..., User]


@pytest.fixture
def make_user(db: Session) -> MakeUser:
    counter = {"n": 0}

    def _make(*roles: Role, username: str | None = None) -> User:
        counter["n"] += 1
        return identity.create_user(
            db,
            actor=None,
            username=username or f"user{counter['n']}",
            display_name=f"Test User {counter['n']}",
            roles=roles,
        )

    return _make


@pytest.fixture
def staff(make_user: MakeUser) -> dict[str, User]:
    return {
        "admin1": make_user(Role.LIMS_ADMIN, username="admin1"),
        "cs1": make_user(Role.CASE_SCIENTIST, username="cs1"),
        "cs2": make_user(Role.CASE_SCIENTIST, username="cs2"),
        "slo1": make_user(Role.SCREENING_LAB_OFFICER, username="slo1"),
        "dlo1": make_user(Role.DNA_LAB_OFFICER, username="dlo1"),
        "dlo2": make_user(Role.DNA_LAB_OFFICER, username="dlo2"),
        "rev1": make_user(Role.REVIEWER, username="rev1"),
        "codis1": make_user(Role.CODIS_SCIENTIST, username="codis1"),
    }


# --- API --------------------------------------------------------------------


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app = create_app()

    def _db() -> Iterator[Session]:
        # Flush per request but leave the outer test transaction to roll back.
        yield db
        db.flush()

    app.dependency_overrides[get_db] = _db
    with TestClient(app) as c:
        yield c


def as_user(username: str, *, reauth: bool = False) -> dict[str, str]:
    headers = {"X-Dev-User": username}
    if reauth:
        headers["X-Dev-Reauth"] = username
    return headers
