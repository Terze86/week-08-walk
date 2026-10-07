import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.modules.identity.models import AccountStatus, Role


class WorkspaceOut(BaseModel):
    key: str
    title: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: str
    email: str | None
    status: AccountStatus
    roles: list[Role]
    laboratory_ids: list[uuid.UUID]


class MeOut(UserOut):
    workspaces: list[WorkspaceOut]


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=100, pattern=r"^[A-Za-z0-9._-]+$")
    display_name: str = Field(min_length=1, max_length=200)
    email: str | None = Field(default=None, max_length=320, pattern=r"^[^@\s]+@[^@\s]+$")
    oidc_subject: str | None = None
    roles: list[Role] = []
    laboratory_ids: list[uuid.UUID] = []


class RolesUpdate(BaseModel):
    roles: list[Role]
    reason: str = Field(min_length=3)


class LaboratoriesUpdate(BaseModel):
    laboratory_ids: list[uuid.UUID]
    reason: str = Field(min_length=3)


class StatusUpdate(BaseModel):
    status: AccountStatus
    reason: str = Field(min_length=3)


class LaboratoryCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=200)


class LaboratoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
