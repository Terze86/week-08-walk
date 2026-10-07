"""Staff accounts, roles and laboratory assignments (WF-01.01, WF-19.01)."""

import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.errors import DomainError, NotFound, PermissionDenied
from app.modules.identity.models import (
    AccountStatus,
    Laboratory,
    Role,
    User,
    UserLaboratory,
    UserRole,
)


def _snapshot(user: User) -> dict[str, object]:
    return {
        "username": user.username,
        "status": user.status.value,
        "roles": sorted(r.value for r in user.roles),
        "laboratory_ids": sorted(str(i) for i in user.laboratory_ids),
    }


def _get(session: Session, user_id: uuid.UUID) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise NotFound("User not found")
    return user


def _require_change(before: dict[str, object], user: User) -> None:
    if _snapshot(user) == before:
        raise DomainError("Nothing to change")


def _not_self(actor: User, user: User, what: str) -> None:
    if actor.id == user.id:
        raise PermissionDenied(f"You cannot change your own {what}")


def _check_labs(session: Session, lab_ids: Iterable[uuid.UUID]) -> set[uuid.UUID]:
    wanted = set(lab_ids)
    found = set(session.execute(select(Laboratory.id).where(Laboratory.id.in_(wanted))).scalars())
    if missing := wanted - found:
        raise NotFound(f"Unknown laboratories: {sorted(str(m) for m in missing)}")
    return wanted


def create_laboratory(session: Session, *, actor: User, code: str, name: str) -> Laboratory:
    if session.execute(select(Laboratory).filter_by(code=code)).scalar_one_or_none():
        raise DomainError(f"Laboratory {code} already exists")
    lab = Laboratory(code=code, name=name)
    session.add(lab)
    session.flush()
    audit.record(
        session,
        actor_id=actor.id,
        action="laboratory.created",
        entity_type="laboratory",
        entity_id=lab.id,
        after={"code": code, "name": name},
    )
    return lab


def create_user(
    session: Session,
    *,
    actor: User | None,
    username: str,
    display_name: str,
    email: str | None = None,
    oidc_subject: str | None = None,
    roles: Iterable[Role] = (),
    laboratory_ids: Iterable[uuid.UUID] = (),
) -> User:
    if session.execute(select(User).filter_by(username=username)).scalar_one_or_none():
        raise DomainError(f"Username {username} is already in use")
    user = User(
        username=username,
        display_name=display_name,
        email=email,
        oidc_subject=oidc_subject,
        status=AccountStatus.ACTIVE,
    )
    user.role_links = [UserRole(role=r) for r in set(roles)]
    user.lab_links = [
        UserLaboratory(laboratory_id=lab) for lab in _check_labs(session, laboratory_ids)
    ]
    session.add(user)
    session.flush()
    audit.record(
        session,
        actor_id=actor.id if actor else None,
        action="user.created",
        entity_type="user",
        entity_id=user.id,
        after=_snapshot(user),
    )
    return user


def set_roles(
    session: Session, *, actor: User, user_id: uuid.UUID, roles: Iterable[Role], reason: str
) -> User:
    user = _get(session, user_id)
    _not_self(actor, user, "roles")
    before = _snapshot(user)
    wanted = set(roles)
    user.role_links = [link for link in user.role_links if link.role in wanted]
    user.role_links += [UserRole(role=r) for r in wanted - user.roles]
    _require_change(before, user)
    session.flush()
    audit.record(
        session,
        actor_id=actor.id,
        action="user.roles_changed",
        entity_type="user",
        entity_id=user.id,
        reason=reason,
        before=before,
        after=_snapshot(user),
    )
    return user


def set_laboratories(
    session: Session,
    *,
    actor: User,
    user_id: uuid.UUID,
    laboratory_ids: Iterable[uuid.UUID],
    reason: str,
) -> User:
    user = _get(session, user_id)
    before = _snapshot(user)
    wanted = _check_labs(session, laboratory_ids)
    user.lab_links = [link for link in user.lab_links if link.laboratory_id in wanted]
    user.lab_links += [UserLaboratory(laboratory_id=lab) for lab in wanted - user.laboratory_ids]
    _require_change(before, user)
    session.flush()
    audit.record(
        session,
        actor_id=actor.id,
        action="user.laboratories_changed",
        entity_type="user",
        entity_id=user.id,
        reason=reason,
        before=before,
        after=_snapshot(user),
    )
    return user


def set_status(
    session: Session, *, actor: User, user_id: uuid.UUID, status: AccountStatus, reason: str
) -> User:
    user = _get(session, user_id)
    _not_self(actor, user, "account status")
    before = _snapshot(user)
    user.status = status
    _require_change(before, user)
    session.flush()
    audit.record(
        session,
        actor_id=actor.id,
        action="user.status_changed",
        entity_type="user",
        entity_id=user.id,
        reason=reason,
        before=before,
        after=_snapshot(user),
    )
    return user


def list_users(session: Session) -> list[User]:
    return list(session.execute(select(User).order_by(User.username)).scalars())


def list_laboratories(session: Session) -> list[Laboratory]:
    return list(session.execute(select(Laboratory).order_by(Laboratory.code)).scalars())
