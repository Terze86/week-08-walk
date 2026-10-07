import uuid
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, CreatedAt, UUIDPk


class Role(StrEnum):
    CASE_SCIENTIST = "case_scientist"
    SCREENING_LAB_OFFICER = "screening_lab_officer"
    DNA_LAB_OFFICER = "dna_lab_officer"
    REVIEWER = "reviewer"
    CODIS_SCIENTIST = "codis_scientist"
    LIMS_ADMIN = "lims_admin"


# Roles that make or record scientific decisions. LIMS Admin rights never
# substitute for one of these (WF-19.04).
SCIENTIFIC_ROLES = frozenset(
    {
        Role.CASE_SCIENTIST,
        Role.SCREENING_LAB_OFFICER,
        Role.DNA_LAB_OFFICER,
        Role.REVIEWER,
        Role.CODIS_SCIENTIST,
    }
)


class AccountStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


role_enum = Enum(Role, name="role", values_callable=lambda e: [m.value for m in e])


class Laboratory(UUIDPk, CreatedAt, Base):
    __tablename__ = "laboratory"

    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(200))


class User(UUIDPk, CreatedAt, Base):
    __tablename__ = "app_user"

    username: Mapped[str] = mapped_column(String(100), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    oidc_subject: Mapped[str | None] = mapped_column(String(200), unique=True)
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, name="account_status", values_callable=lambda e: [m.value for m in e]),
        default=AccountStatus.ACTIVE,
    )

    role_links: Mapped[list["UserRole"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    lab_links: Mapped[list["UserLaboratory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def roles(self) -> set[Role]:
        return {link.role for link in self.role_links}

    @property
    def laboratory_ids(self) -> set[uuid.UUID]:
        return {link.laboratory_id for link in self.lab_links}

    @property
    def is_active(self) -> bool:
        return self.status == AccountStatus.ACTIVE

    def has_role(self, *roles: Role) -> bool:
        return bool(self.roles.intersection(roles))


class UserRole(Base):
    __tablename__ = "user_role"
    __table_args__ = (UniqueConstraint("user_id", "role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"))
    role: Mapped[Role] = mapped_column(role_enum)

    user: Mapped[User] = relationship(back_populates="role_links")


class UserLaboratory(Base):
    __tablename__ = "user_laboratory"
    __table_args__ = (UniqueConstraint("user_id", "laboratory_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"))
    laboratory_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("laboratory.id"))

    user: Mapped[User] = relationship(back_populates="lab_links")
