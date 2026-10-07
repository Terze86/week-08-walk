"""Shared fixtures for casework tests (sections 2 and 3)."""

import base64
from dataclasses import dataclass

import pytest
from sqlalchemy.orm import Session

from app.modules.cases import service as cases
from app.modules.cases.models import Case, Exhibit, Subcase, SubmissionSource
from app.modules.identity.models import User
from app.modules.receipt import service as receipts
from app.modules.reference import service as reference
from app.modules.reference.models import Client, Location, LocationKind

# A valid 1x1 transparent PNG, standing in for a captured signature.
SIGNATURE_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


@dataclass
class Setting:
    client: Client
    store_a: Location
    store_b: Location
    bench: Location


@pytest.fixture
def setting(db: Session, staff: dict[str, User], lab) -> Setting:
    admin = staff["admin1"]
    return Setting(
        client=reference.create_client(db, actor=admin, code="SPF-A", name="Police Division A"),
        store_a=reference.create_location(
            db,
            actor=admin,
            code="STORE-A",
            name="Exhibit store A",
            kind=LocationKind.STORAGE,
            laboratory_id=lab.id,
        ),
        store_b=reference.create_location(
            db,
            actor=admin,
            code="STORE-B",
            name="Exhibit store B",
            kind=LocationKind.STORAGE,
            laboratory_id=lab.id,
        ),
        bench=reference.create_location(
            db,
            actor=admin,
            code="BENCH-1",
            name="Screening bench 1",
            kind=LocationKind.BENCH,
            laboratory_id=lab.id,
        ),
    )


def register(db: Session, actor: User, lab, setting: Setting) -> tuple[Case, Subcase]:
    return cases.register_case(
        db,
        actor=actor,
        laboratory_id=lab.id,
        client_id=setting.client.id,
        client_reference="IR/2026/0412",
        source=SubmissionSource.PAPER,
        submitter_name="SSgt Tan",
        submitter_contact="6123 4567",
        investigating_officer_name="Insp Lee",
        case_information="Burglary at 12 Example Road",
    )


def accepted(db: Session, actor: User, subcase: Subcase, description: str) -> Exhibit:
    exhibit = cases.add_exhibit(
        db,
        actor=actor,
        subcase_id=subcase.id,
        description=description,
        marking="A1",
        seal="Seal 0001",
    )
    return cases.accept_exhibit(
        db,
        actor=actor,
        exhibit_id=exhibit.id,
        description_matches=True,
        marking_matches=True,
        seal_intact=True,
    )


@pytest.fixture
def received(db: Session, staff, lab, setting, file_store) -> tuple[Subcase, list[Exhibit]]:
    """A subcase with two exhibits received by cs1 (cs1 holds them)."""
    cs = staff["cs1"]
    _, subcase = register(db, cs, lab, setting)
    exhibits = [accepted(db, cs, subcase, "Blue shirt"), accepted(db, cs, subcase, "Knife")]
    receipt = receipts.prepare_receipt(
        db, actor=cs, subcase_id=subcase.id, exhibit_ids=[e.id for e in exhibits]
    )
    receipts.complete_receipt(
        db,
        actor=cs,
        store=file_store,
        receipt_id=receipt.id,
        signature_png=SIGNATURE_PNG,
        actual_submitter_name="Cpl Ong",
    )
    return subcase, exhibits
