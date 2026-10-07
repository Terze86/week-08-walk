import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.cases.models import CaseState, ExhibitState, SubcaseState, SubmissionSource


class Person(BaseModel):
    id: uuid.UUID
    display_name: str


class CaseRegister(BaseModel):
    laboratory_id: uuid.UUID
    client_id: uuid.UUID
    client_reference: str = Field(min_length=1, max_length=100)
    source: SubmissionSource
    submission_reference: str | None = Field(default=None, max_length=100)
    submitter_name: str = Field(min_length=1, max_length=200)
    submitter_contact: str | None = Field(default=None, max_length=300)
    investigating_officer_name: str = Field(min_length=1, max_length=200)
    investigating_officer_contact: str | None = Field(default=None, max_length=300)
    case_information: str | None = None


class CaseCorrection(BaseModel):
    changes: dict[str, str | None]
    reason: str = Field(min_length=3)


class CaseSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_number: str
    client_reference: str
    state: CaseState
    created_at: datetime


class CaseOut(CaseSummary):
    laboratory_id: uuid.UUID
    client_id: uuid.UUID
    source: SubmissionSource
    submission_reference: str | None
    submitter_name: str
    submitter_contact: str | None
    investigating_officer_name: str
    investigating_officer_contact: str | None
    case_information: str | None


class SubcaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subcase_number: str
    case_id: uuid.UUID
    state: SubcaseState
    created_at: datetime
    case_scientist: Person | None = None


class CaseDetail(BaseModel):
    case: CaseOut
    subcases: list[SubcaseOut]


class ExhibitIn(BaseModel):
    description: str = Field(min_length=1)
    marking: str | None = None
    seal: str | None = None
    submitter_item_ref: str | None = Field(default=None, max_length=100)


class ExhibitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    barcode: str
    subcase_id: uuid.UUID
    submitter_item_ref: str | None
    description: str
    marking: str | None
    seal: str | None
    state: ExhibitState
    description_matches: bool | None
    marking_matches: bool | None
    seal_intact: bool | None
    check_notes: str | None
    rejection_reason: str | None
    receipt_id: uuid.UUID | None
    examiner: Person | None = None


class AcceptIn(BaseModel):
    description_matches: bool
    marking_matches: bool
    seal_intact: bool
    notes: str | None = None


class RejectIn(BaseModel):
    reason: str = Field(min_length=3)
    description_matches: bool | None = None
    marking_matches: bool | None = None
    seal_intact: bool | None = None


class ReasonIn(BaseModel):
    reason: str = Field(min_length=3)


class AssignIn(BaseModel):
    user_id: uuid.UUID | None = None
    reason: str | None = None
