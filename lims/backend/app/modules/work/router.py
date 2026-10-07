"""Each person's work queue and colleague list (WF-01.05)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.db import get_db
from app.modules.cases import policy
from app.modules.cases import service as cases
from app.modules.cases.router import exhibit_out, subcase_out
from app.modules.cases.schemas import ExhibitOut, SubcaseOut
from app.modules.custody import service as custody
from app.modules.custody.router import CorrectionOut, HandoverOut, correction_out, incoming
from app.modules.identity import service as identity
from app.modules.identity.models import Role
from app.modules.receipt import service as receipts
from app.modules.receipt.router import ReceiptSummary

router = APIRouter(tags=["work"])
Db = Annotated[Session, Depends(get_db)]


class Colleague(BaseModel):
    id: uuid.UUID
    display_name: str
    roles: list[Role]


class MyWork(BaseModel):
    subcases: list[SubcaseOut]
    examinations: list[ExhibitOut]
    incoming_handovers: list[HandoverOut]
    receipt_exceptions: list[ReceiptSummary]
    corrections_to_decide: list[CorrectionOut]


@router.get("/my-work", response_model=MyWork)
def my_work(db: Db, user: CurrentUser) -> MyWork:
    authorizer = bool(user.roles & policy.CORRECTION_AUTHORIZER_ROLES)
    reception = bool(user.roles & policy.RECEPTION_ROLES)
    return MyWork(
        subcases=[subcase_out(db, s) for s in cases.my_subcases(db, user)],
        examinations=[exhibit_out(db, e) for e in cases.my_examinations(db, user)],
        incoming_handovers=incoming(db, user),
        receipt_exceptions=[
            ReceiptSummary.model_validate(r) for r in receipts.open_exceptions(db, user)
        ]
        if reception
        else [],
        corrections_to_decide=[correction_out(db, c) for c in custody.pending_corrections(db, user)]
        if authorizer
        else [],
    )


@router.get("/staff", response_model=list[Colleague])
def colleagues(db: Db, user: CurrentUser) -> list[Colleague]:
    """Active casework colleagues in the caller's laboratories (for assignment
    and handover pickers)."""
    return [
        Colleague(id=u.id, display_name=u.display_name, roles=sorted(u.roles))
        for u in identity.list_users(db)
        if u.is_active
        and u.roles & policy.CASEWORK_ROLES
        and u.laboratory_ids & user.laboratory_ids
    ]
