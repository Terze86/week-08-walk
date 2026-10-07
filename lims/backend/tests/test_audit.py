import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core import audit
from app.modules.identity.models import Role

pytestmark = pytest.mark.urs("WF-19.06")


def test_events_form_a_verifiable_hash_chain(db: Session, make_user) -> None:
    actor = make_user(Role.LIMS_ADMIN)
    first = audit.record(db, actor_id=actor.id, action="x.created", entity_type="x", entity_id=1)
    second = audit.record(
        db,
        actor_id=actor.id,
        action="x.changed",
        entity_type="x",
        entity_id=1,
        reason="typo in description",
        before={"description": "Blue shrit"},
        after={"description": "Blue shirt"},
    )
    assert second.prev_hash == first.hash
    assert audit.verify_chain(db) == []
    assert [e.action for e in audit.history(db, "x", 1)] == ["x.created", "x.changed"]
    assert second.reason == "typo in description"


def test_tampering_is_detected_even_if_trigger_is_bypassed(db: Session, make_user) -> None:
    actor = make_user(Role.LIMS_ADMIN)
    event = audit.record(
        db, actor_id=actor.id, action="x.created", entity_type="x", entity_id=1, after={"v": 1}
    )
    audit.record(db, actor_id=actor.id, action="x.changed", entity_type="x", entity_id=1)
    # Simulate a privileged out-of-band edit. Production DB roles cannot do this
    # (the application role does not own the tables); the chain still exposes it.
    db.execute(text("ALTER TABLE audit_event DISABLE TRIGGER audit_event_append_only"))
    db.execute(
        text("UPDATE audit_event SET after = '{\"v\": 2}'::jsonb WHERE id = :id"), {"id": event.id}
    )
    db.execute(text("ALTER TABLE audit_event ENABLE TRIGGER audit_event_append_only"))
    db.expire_all()
    assert audit.verify_chain(db) == [event.id]
