import hashlib

import pytest
from sqlalchemy.orm import Session

from app.core import files
from app.core.errors import IntegrityFailure
from app.modules.identity.models import Role


def test_store_and_read_back_verified(db: Session, make_user, file_store) -> None:
    user = make_user(Role.SCREENING_LAB_OFFICER)
    data = b"\x89PNG original photograph bytes"
    record = files.store_file(
        db, file_store, data=data, original_name="ex1.png", media_type="image/png", actor_id=user.id
    )
    assert record.sha256 == hashlib.sha256(data).hexdigest()
    got, content = files.read_file(db, file_store, record.id)
    assert content == data and got.original_name == "ex1.png"


def test_identical_content_is_stored_once_but_each_upload_is_recorded(
    db: Session, make_user, file_store
) -> None:
    user = make_user(Role.CASE_SCIENTIST)
    a = files.store_file(
        db,
        file_store,
        data=b"same",
        original_name="a.txt",
        media_type="text/plain",
        actor_id=user.id,
    )
    b = files.store_file(
        db,
        file_store,
        data=b"same",
        original_name="b.txt",
        media_type="text/plain",
        actor_id=user.id,
    )
    assert a.id != b.id and a.storage_key == b.storage_key


def test_store_refuses_to_overwrite(file_store) -> None:
    file_store.put("k", b"one")
    with pytest.raises(FileExistsError):
        file_store.put("k", b"two")
    assert file_store.get("k") == b"one"


def test_corrupted_object_fails_integrity_check(db: Session, make_user, file_store) -> None:
    user = make_user(Role.CASE_SCIENTIST)
    record = files.store_file(
        db,
        file_store,
        data=b"genuine",
        original_name="g.txt",
        media_type="text/plain",
        actor_id=user.id,
    )
    path = file_store._path(record.storage_key)
    path.chmod(0o644)
    path.write_bytes(b"altered")
    with pytest.raises(IntegrityFailure):
        files.read_file(db, file_store, record.id)


def test_storage_keys_cannot_escape_the_root(file_store) -> None:
    with pytest.raises(ValueError):
        file_store.put("../outside", b"x")
