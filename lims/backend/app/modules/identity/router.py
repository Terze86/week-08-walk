import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser, require_roles
from app.core.db import get_db
from app.core.workspaces import workspaces_for
from app.modules.identity import service
from app.modules.identity.models import Role, User
from app.modules.identity.schemas import (
    LaboratoriesUpdate,
    LaboratoryCreate,
    LaboratoryOut,
    MeOut,
    RolesUpdate,
    StatusUpdate,
    UserCreate,
    UserOut,
    WorkspaceOut,
)

router = APIRouter(tags=["identity"])
Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_roles(Role.LIMS_ADMIN))]


@router.get("/me", response_model=MeOut)
def me(user: CurrentUser) -> MeOut:
    return MeOut(
        **UserOut.model_validate(user).model_dump(),
        workspaces=[WorkspaceOut(key=w.key, title=w.title) for w in workspaces_for(user.roles)],
    )


@router.get("/admin/users", response_model=list[UserOut])
def list_users(db: Db, _: Admin) -> list[User]:
    return service.list_users(db)


@router.post("/admin/users", response_model=UserOut, status_code=201)
def create_user(body: UserCreate, db: Db, actor: Admin) -> User:
    return service.create_user(db, actor=actor, **body.model_dump())


@router.put("/admin/users/{user_id}/roles", response_model=UserOut)
def set_roles(user_id: uuid.UUID, body: RolesUpdate, db: Db, actor: Admin) -> User:
    return service.set_roles(db, actor=actor, user_id=user_id, roles=body.roles, reason=body.reason)


@router.put("/admin/users/{user_id}/laboratories", response_model=UserOut)
def set_laboratories(user_id: uuid.UUID, body: LaboratoriesUpdate, db: Db, actor: Admin) -> User:
    return service.set_laboratories(
        db, actor=actor, user_id=user_id, laboratory_ids=body.laboratory_ids, reason=body.reason
    )


@router.put("/admin/users/{user_id}/status", response_model=UserOut)
def set_status(user_id: uuid.UUID, body: StatusUpdate, db: Db, actor: Admin) -> User:
    return service.set_status(
        db, actor=actor, user_id=user_id, status=body.status, reason=body.reason
    )


@router.get("/admin/laboratories", response_model=list[LaboratoryOut])
def list_laboratories(db: Db, _: CurrentUser) -> list:
    return service.list_laboratories(db)


@router.post("/admin/laboratories", response_model=LaboratoryOut, status_code=201)
def create_laboratory(body: LaboratoryCreate, db: Db, actor: Admin) -> object:
    return service.create_laboratory(db, actor=actor, code=body.code, name=body.name)
