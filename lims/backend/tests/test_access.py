import pytest
from sqlalchemy.orm import Session

from app.core import access, audit
from app.core.access import GrantKind
from app.core.errors import DomainError, NotFound, ReasonRequired


def test_assignment_grants_and_revokes_access(db: Session, staff) -> None:
    cs, admin = staff["cs1"], staff["admin1"]
    assert not access.has_grant(db, cs.id, "subcase", "LAB2026-000001")
    g = access.grant(
        db,
        actor_id=admin.id,
        user_id=cs.id,
        entity_type="subcase",
        entity_id="LAB2026-000001",
        kind=GrantKind.ASSIGNMENT,
    )
    assert access.has_grant(db, cs.id, "subcase", "LAB2026-000001")
    with pytest.raises(DomainError):
        access.grant(
            db,
            actor_id=admin.id,
            user_id=cs.id,
            entity_type="subcase",
            entity_id="LAB2026-000001",
            kind=GrantKind.ASSIGNMENT,
        )
    with pytest.raises(ReasonRequired):
        access.revoke(db, actor_id=admin.id, grant_id=g.id, reason="")
    access.revoke(db, actor_id=admin.id, grant_id=g.id, reason="Reassigned to cs2")
    assert not access.has_grant(db, cs.id, "subcase", "LAB2026-000001")
    with pytest.raises(NotFound):
        access.revoke(db, actor_id=admin.id, grant_id=g.id, reason="again")
    actions = [e.action for e in audit.history(db, "subcase", "LAB2026-000001")]
    assert actions == ["access.granted", "access.revoked"]


def test_codis_share_is_limited_to_named_items(db: Session, staff) -> None:
    codis, cs = staff["codis1"], staff["cs1"]
    access.grant(
        db,
        actor_id=cs.id,
        user_id=codis.id,
        entity_type="profile_version",
        entity_id="P1",
        kind=GrantKind.CODIS_SHARE,
    )
    shared = access.granted_entity_ids(
        db, codis.id, "profile_version", kinds=(GrantKind.CODIS_SHARE,)
    )
    assert shared == {"P1"}
    assert not access.has_grant(db, codis.id, "profile_version", "P2")
    assert not access.has_grant(
        db, codis.id, "profile_version", "P1", kinds=(GrantKind.ASSIGNMENT,)
    )
