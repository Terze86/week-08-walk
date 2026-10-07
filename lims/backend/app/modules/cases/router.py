import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.db import get_db
from app.modules.cases import policy, service
from app.modules.cases.models import Exhibit, Subcase
from app.modules.cases.schemas import (
    AcceptIn,
    AssignIn,
    CaseCorrection,
    CaseDetail,
    CaseOut,
    CaseRegister,
    CaseSummary,
    ExhibitIn,
    ExhibitOut,
    Person,
    ReasonIn,
    RejectIn,
    SubcaseOut,
)
from app.modules.identity.models import User
from app.modules.items.models import Item

router = APIRouter(tags=["cases"])
Db = Annotated[Session, Depends(get_db)]


def person(db: Session, user_id: uuid.UUID | None) -> Person | None:
    user = db.get(User, user_id) if user_id else None
    return Person(id=user.id, display_name=user.display_name) if user else None


def subcase_out(db: Session, subcase: Subcase) -> SubcaseOut:
    assignees = policy.assignee_ids(db, policy.SUBCASE, subcase.id)
    out = SubcaseOut.model_validate(subcase)
    out.case_scientist = person(db, next(iter(assignees), None))
    return out


def exhibit_out(db: Session, exhibit: Exhibit) -> ExhibitOut:
    item = db.get(Item, exhibit.id)
    assert item is not None
    examiners = policy.assignee_ids(db, policy.EXHIBIT_EXAMINATION, exhibit.id)
    return ExhibitOut.model_validate(
        {
            **{c: getattr(exhibit, c) for c in ExhibitOut.model_fields if hasattr(exhibit, c)},
            "barcode": item.barcode,
            "examiner": person(db, next(iter(examiners), None)),
        }
    )


@router.get("/cases", response_model=list[CaseSummary])
def search(db: Db, user: CurrentUser, q: str | None = None) -> list:
    return service.search_cases(db, user, q)


@router.post("/cases", response_model=CaseDetail, status_code=201)
def register(body: CaseRegister, db: Db, user: CurrentUser) -> CaseDetail:
    case, subcase = service.register_case(db, actor=user, **body.model_dump())
    return CaseDetail(case=CaseOut.model_validate(case), subcases=[subcase_out(db, subcase)])


@router.get("/cases/{case_id}", response_model=CaseDetail)
def case_detail(case_id: uuid.UUID, db: Db, user: CurrentUser) -> CaseDetail:
    case = service.get_case(db, user, case_id)
    subcases = db.execute(
        select(Subcase).where(Subcase.case_id == case.id).order_by(Subcase.created_at)
    ).scalars()
    return CaseDetail(
        case=CaseOut.model_validate(case), subcases=[subcase_out(db, s) for s in subcases]
    )


@router.patch("/cases/{case_id}", response_model=CaseOut)
def correct_case(case_id: uuid.UUID, body: CaseCorrection, db: Db, user: CurrentUser) -> object:
    return service.update_case_details(
        db, actor=user, case_id=case_id, changes=body.changes, reason=body.reason
    )


@router.post("/cases/{case_id}/subcases", response_model=SubcaseOut, status_code=201)
def new_subcase(case_id: uuid.UUID, db: Db, user: CurrentUser) -> SubcaseOut:
    return subcase_out(db, service.create_subcase(db, actor=user, case_id=case_id))


@router.get("/subcases/{subcase_id}", response_model=SubcaseOut)
def subcase(subcase_id: uuid.UUID, db: Db, user: CurrentUser) -> SubcaseOut:
    return subcase_out(db, service.get_subcase(db, user, subcase_id))


@router.post("/subcases/{subcase_id}/assignment", response_model=SubcaseOut)
def assign_scientist(
    subcase_id: uuid.UUID, body: AssignIn, db: Db, user: CurrentUser
) -> SubcaseOut:
    if body.user_id is None:
        body.user_id = user.id
    service.assign_case_scientist(
        db, actor=user, subcase_id=subcase_id, user_id=body.user_id, reason=body.reason
    )
    return subcase_out(db, service.get_subcase(db, user, subcase_id))


@router.get("/subcases/{subcase_id}/exhibits", response_model=list[ExhibitOut])
def exhibits(subcase_id: uuid.UUID, db: Db, user: CurrentUser) -> list[ExhibitOut]:
    service.get_subcase(db, user, subcase_id)
    return [exhibit_out(db, e) for e in service.list_exhibits(db, subcase_id)]


@router.post("/subcases/{subcase_id}/exhibits", response_model=ExhibitOut, status_code=201)
def add_exhibit(subcase_id: uuid.UUID, body: ExhibitIn, db: Db, user: CurrentUser) -> ExhibitOut:
    exhibit = service.add_exhibit(db, actor=user, subcase_id=subcase_id, **body.model_dump())
    return exhibit_out(db, exhibit)


@router.post("/exhibits/{exhibit_id}/accept", response_model=ExhibitOut)
def accept(exhibit_id: uuid.UUID, body: AcceptIn, db: Db, user: CurrentUser) -> ExhibitOut:
    return exhibit_out(
        db, service.accept_exhibit(db, actor=user, exhibit_id=exhibit_id, **body.model_dump())
    )


@router.post("/exhibits/{exhibit_id}/reject", response_model=ExhibitOut)
def reject(exhibit_id: uuid.UUID, body: RejectIn, db: Db, user: CurrentUser) -> ExhibitOut:
    return exhibit_out(
        db, service.reject_exhibit(db, actor=user, exhibit_id=exhibit_id, **body.model_dump())
    )


@router.post("/exhibits/{exhibit_id}/reconsider", response_model=ExhibitOut)
def reconsider(exhibit_id: uuid.UUID, body: ReasonIn, db: Db, user: CurrentUser) -> ExhibitOut:
    return exhibit_out(
        db, service.reconsider_exhibit(db, actor=user, exhibit_id=exhibit_id, reason=body.reason)
    )


@router.post("/exhibits/{exhibit_id}/examination", response_model=ExhibitOut)
def assign_examination(
    exhibit_id: uuid.UUID, body: AssignIn, db: Db, user: CurrentUser
) -> ExhibitOut:
    service.assign_examination(
        db, actor=user, exhibit_id=exhibit_id, user_id=body.user_id, reason=body.reason
    )
    return exhibit_out(db, service.get_exhibit(db, user, exhibit_id))
