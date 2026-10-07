"""Declarative state machines for per-item workflow state.

Each workflow entity (exhibit, sample, batch, report version, ...) holds its
own `state` column, so items progress independently of the rest of their case
(WF-04.08, WF-05.07). A transition names the states it may leave, the state it
enters, the roles allowed to perform it, whether a reason is mandatory, and any
guards (separation-of-duties checks, completeness checks). Applying a
transition always writes an audit event in the same transaction.
"""

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.core import audit
from app.core.errors import InvalidTransition, PermissionDenied, ReasonRequired
from app.modules.identity.models import Role, User


class WorkflowEntity(Protocol):
    id: Any


@dataclass(frozen=True)
class GuardContext:
    session: Session
    actor: User
    entity: Any
    reason: str | None
    data: Mapping[str, Any]


Guard = Callable[[GuardContext], None]
"""A guard raises a DomainError to block the transition."""


@dataclass(frozen=True)
class Transition:
    name: str
    source: frozenset[str]
    target: str
    roles: frozenset[Role]
    reason_required: bool = False
    guards: tuple[Guard, ...] = ()


@dataclass
class StateMachine:
    entity_type: str
    states: frozenset[str]
    initial: str
    transitions: Mapping[str, Transition] = field(default_factory=dict)
    state_attr: str = "state"

    @classmethod
    def build(
        cls,
        entity_type: str,
        *,
        states: Iterable[str],
        initial: str,
        transitions: Iterable[Transition],
        state_attr: str = "state",
    ) -> "StateMachine":
        state_set = frozenset(states)
        by_name: dict[str, Transition] = {}
        if initial not in state_set:
            raise ValueError(f"{entity_type}: initial state {initial!r} is not a declared state")
        for t in transitions:
            if t.name in by_name:
                raise ValueError(f"{entity_type}: duplicate transition {t.name!r}")
            unknown = (t.source | {t.target}) - state_set
            if unknown:
                raise ValueError(f"{entity_type}.{t.name}: unknown states {sorted(unknown)}")
            if not t.roles:
                raise ValueError(f"{entity_type}.{t.name}: no roles may perform it")
            by_name[t.name] = t
        return cls(entity_type, state_set, initial, by_name, state_attr)

    def state_of(self, entity: Any) -> str:
        return str(getattr(entity, self.state_attr))

    def available(self, entity: Any, actor: User) -> list[str]:
        """Transitions the actor could attempt from the entity's current state."""
        current = self.state_of(entity)
        return [
            t.name
            for t in self.transitions.values()
            if current in t.source and actor.roles & t.roles
        ]

    def apply(
        self,
        session: Session,
        entity: Any,
        transition: str,
        *,
        actor: User,
        reason: str | None = None,
        data: Mapping[str, Any] | None = None,
    ) -> audit.AuditEvent:
        t = self.transitions.get(transition)
        if t is None:
            raise InvalidTransition(f"{self.entity_type} has no transition {transition!r}")
        current = self.state_of(entity)
        if current not in t.source:
            raise InvalidTransition(f"Cannot {transition} {self.entity_type} in state {current!r}")
        if not actor.is_active:
            raise PermissionDenied("Account is disabled")
        if not actor.roles & t.roles:
            raise PermissionDenied(
                f"{transition} on {self.entity_type} requires one of: "
                + ", ".join(sorted(r.value for r in t.roles))
            )
        reason = reason.strip() if reason else None
        if t.reason_required and not reason:
            raise ReasonRequired(f"{transition} on {self.entity_type} requires a reason")

        payload = dict(data or {})
        ctx = GuardContext(session, actor, entity, reason, payload)
        for guard in t.guards:
            guard(ctx)

        setattr(entity, self.state_attr, t.target)
        return audit.record(
            session,
            actor_id=actor.id,
            action=f"{self.entity_type}.{t.name}",
            entity_type=self.entity_type,
            entity_id=entity.id,
            reason=reason,
            before={"state": current},
            after={"state": t.target, **payload},
        )
