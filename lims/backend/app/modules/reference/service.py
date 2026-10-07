"""Reference data maintained by the LIMS Admin (WF-19.02)."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.errors import DomainError, NotFound
from app.modules.identity.models import Laboratory, User
from app.modules.reference.models import Client, Location, LocationKind


def create_client(session: Session, *, actor: User, code: str, name: str) -> Client:
    if session.execute(select(Client).filter_by(code=code)).scalar_one_or_none():
        raise DomainError(f"Client {code} already exists")
    client = Client(code=code, name=name, active=True)
    session.add(client)
    session.flush()
    audit.record(
        session,
        actor_id=actor.id,
        action="client.created",
        entity_type="client",
        entity_id=client.id,
        after={"code": code, "name": name},
    )
    return client


def create_location(
    session: Session,
    *,
    actor: User,
    code: str,
    name: str,
    kind: LocationKind,
    laboratory_id: uuid.UUID,
) -> Location:
    if session.get(Laboratory, laboratory_id) is None:
        raise NotFound("Laboratory not found")
    if session.execute(select(Location).filter_by(code=code)).scalar_one_or_none():
        raise DomainError(f"Location {code} already exists")
    location = Location(code=code, name=name, kind=kind, laboratory_id=laboratory_id, active=True)
    session.add(location)
    session.flush()
    audit.record(
        session,
        actor_id=actor.id,
        action="location.created",
        entity_type="location",
        entity_id=location.id,
        after={"code": code, "name": name, "kind": kind.value},
    )
    return location


def set_location_active(
    session: Session, *, actor: User, location_id: uuid.UUID, active: bool, reason: str
) -> Location:
    location = session.get(Location, location_id)
    if location is None:
        raise NotFound("Location not found")
    if location.active == active:
        raise DomainError("Nothing to change")
    location.active = active
    audit.record(
        session,
        actor_id=actor.id,
        action="location.activated" if active else "location.deactivated",
        entity_type="location",
        entity_id=location.id,
        reason=reason,
    )
    return location


def list_clients(session: Session) -> list[Client]:
    return list(session.execute(select(Client).order_by(Client.name)).scalars())


def list_locations(
    session: Session, laboratory_ids: set[uuid.UUID] | None = None
) -> list[Location]:
    query = select(Location).order_by(Location.code)
    if laboratory_ids is not None:
        query = query.where(Location.laboratory_id.in_(laboratory_ids))
    return list(session.execute(query).scalars())
