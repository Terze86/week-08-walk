import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core import audit, documents, files
from app.core.db import APPEND_ONLY_TABLES
from app.modules.identity.models import Role

pytestmark = pytest.mark.urs("WF-19.04", "WF-19.06")


def test_migrations_protect_every_append_only_model(db: Session) -> None:
    protected = set(
        db.execute(
            text(
                "SELECT c.relname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
                "WHERE t.tgname = c.relname || '_append_only' AND t.tgenabled = 'O'"
            )
        ).scalars()
    )
    assert set(APPEND_ONLY_TABLES) <= protected


@pytest.fixture
def populated(db: Session, make_user, file_store, received) -> None:
    actor = make_user(Role.CASE_SCIENTIST)
    audit.record(db, actor_id=actor.id, action="a", entity_type="t", entity_id=uuid.uuid4())
    stored = files.store_file(
        db, file_store, data=b"x", original_name="x.txt", media_type="text/plain", actor_id=actor.id
    )
    version = documents.create_document(
        db,
        actor=actor,
        doc_type="t",
        subject_type="s",
        subject_id=1,
        title="t",
        content={"a": 1},
        file=stored,
    )
    from datetime import UTC, datetime

    documents.sign(
        db,
        actor=actor,
        version=version,
        meaning=documents.SignatureMeaning.COMPLETED,
        reauth=documents.ReauthProof(actor.id, datetime.now(UTC)),
    )
    db.flush()


@pytest.mark.parametrize("table", sorted(APPEND_ONLY_TABLES))
@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE {t} SET {col} = {col}",
        "DELETE FROM {t}",
        "TRUNCATE {t} CASCADE",
    ],
)
def test_direct_mutation_is_rejected(
    db: Session, populated: None, table: str, statement: str
) -> None:
    col = "id"
    sql = statement.format(t=table, col=col)
    with pytest.raises(DBAPIError, match="append-only"), db.begin_nested():
        db.execute(text(sql))
