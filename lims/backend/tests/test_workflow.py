import uuid
from dataclasses import dataclass, field

import pytest
from sqlalchemy.orm import Session

from app.core import audit
from app.core.errors import InvalidTransition, PermissionDenied, ReasonRequired
from app.core.workflow import GuardContext, StateMachine, Transition
from app.modules.identity import service as identity
from app.modules.identity.models import AccountStatus, Role


@dataclass
class Exhibit:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    state: str = "received"


def _no_rejecting_sealed(ctx: GuardContext) -> None:
    if ctx.data.get("seal") == "intact" and ctx.entity.state == "received":
        raise InvalidTransition("seal is intact")


MACHINE = StateMachine.build(
    "exhibit",
    states=["received", "accepted", "rejected"],
    initial="received",
    transitions=[
        Transition("accept", frozenset({"received"}), "accepted", frozenset({Role.CASE_SCIENTIST})),
        Transition(
            "reject",
            frozenset({"received"}),
            "rejected",
            frozenset({Role.CASE_SCIENTIST}),
            reason_required=True,
            guards=(_no_rejecting_sealed,),
        ),
    ],
)


@pytest.mark.urs("WF-19.06")
def test_transition_changes_state_and_is_audited(db: Session, make_user) -> None:
    cs = make_user(Role.CASE_SCIENTIST)
    exhibit = Exhibit()
    event = MACHINE.apply(db, exhibit, "accept", actor=cs)
    assert exhibit.state == "accepted"
    assert event.action == "exhibit.accept"
    assert event.before == {"state": "received"}
    assert event.after == {"state": "accepted"}
    assert [e.id for e in audit.history(db, "exhibit", exhibit.id)] == [event.id]


def test_reason_is_required_where_configured(db: Session, make_user) -> None:
    cs = make_user(Role.CASE_SCIENTIST)
    exhibit = Exhibit()
    with pytest.raises(ReasonRequired):
        MACHINE.apply(db, exhibit, "reject", actor=cs, reason="   ")
    MACHINE.apply(db, exhibit, "reject", actor=cs, reason="Seal broken on arrival")
    assert exhibit.state == "rejected"


def test_wrong_state_role_or_guard_blocks_transition(db: Session, make_user) -> None:
    cs = make_user(Role.CASE_SCIENTIST)
    slo = make_user(Role.SCREENING_LAB_OFFICER)
    exhibit = Exhibit()
    with pytest.raises(PermissionDenied):
        MACHINE.apply(db, exhibit, "accept", actor=slo)
    with pytest.raises(InvalidTransition):
        MACHINE.apply(db, exhibit, "reject", actor=cs, reason="r", data={"seal": "intact"})
    MACHINE.apply(db, exhibit, "accept", actor=cs)
    with pytest.raises(InvalidTransition):
        MACHINE.apply(db, exhibit, "accept", actor=cs)
    with pytest.raises(InvalidTransition):
        MACHINE.apply(db, exhibit, "destroy", actor=cs)
    assert MACHINE.available(Exhibit(), cs) == ["accept", "reject"]
    assert MACHINE.available(Exhibit(), slo) == []


@pytest.mark.urs("WF-19.01")
def test_disabled_account_cannot_act(db: Session, make_user) -> None:
    admin = make_user(Role.LIMS_ADMIN)
    cs = make_user(Role.CASE_SCIENTIST)
    identity.set_status(
        db, actor=admin, user_id=cs.id, status=AccountStatus.DISABLED, reason="left"
    )
    with pytest.raises(PermissionDenied):
        MACHINE.apply(db, Exhibit(), "accept", actor=cs)


def test_definition_errors_are_caught_at_build_time() -> None:
    roles = frozenset({Role.CASE_SCIENTIST})
    with pytest.raises(ValueError, match="unknown states"):
        StateMachine.build(
            "x",
            states=["a"],
            initial="a",
            transitions=[Transition("t", frozenset({"a"}), "b", roles)],
        )
    with pytest.raises(ValueError, match="duplicate"):
        StateMachine.build(
            "x",
            states=["a"],
            initial="a",
            transitions=[Transition("t", frozenset({"a"}), "a", roles)] * 2,
        )
    with pytest.raises(ValueError, match="no roles"):
        StateMachine.build(
            "x",
            states=["a"],
            initial="a",
            transitions=[Transition("t", frozenset({"a"}), "a", frozenset())],
        )
