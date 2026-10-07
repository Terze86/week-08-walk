import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, require_roles
from app.core.db import get_db
from app.modules.identity.models import Role, User
from app.modules.reference import service
from app.modules.reference.models import LocationKind

router = APIRouter(tags=["reference"])
Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_roles(Role.LIMS_ADMIN))]


class ClientIn(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=200)


class ClientOut(ClientIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    active: bool


class LocationIn(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    kind: LocationKind
    laboratory_id: uuid.UUID


class LocationOut(LocationIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    active: bool


class ActiveIn(BaseModel):
    active: bool
    reason: str = Field(min_length=3)


@router.get("/clients", response_model=list[ClientOut])
def clients(db: Db, _: CurrentUser) -> list:
    return service.list_clients(db)


@router.post("/admin/clients", response_model=ClientOut, status_code=201)
def create_client(body: ClientIn, db: Db, actor: Admin) -> object:
    return service.create_client(db, actor=actor, code=body.code, name=body.name)


@router.get("/locations", response_model=list[LocationOut])
def locations(db: Db, user: CurrentUser) -> list:
    labs = None if user.has_role(Role.LIMS_ADMIN) else user.laboratory_ids
    return service.list_locations(db, labs)


@router.post("/admin/locations", response_model=LocationOut, status_code=201)
def create_location(body: LocationIn, db: Db, actor: Admin) -> object:
    return service.create_location(db, actor=actor, **body.model_dump())


@router.put("/admin/locations/{location_id}/active", response_model=LocationOut)
def set_active(location_id: uuid.UUID, body: ActiveIn, db: Db, actor: Admin) -> object:
    return service.set_location_active(
        db, actor=actor, location_id=location_id, active=body.active, reason=body.reason
    )
