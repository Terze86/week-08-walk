import pytest
from sqlalchemy.orm import Session

from app.core import audit
from app.core.errors import DomainError, InvalidTransition, NotFound, PermissionDenied
from app.modules.cases import service as cases
from app.modules.cases.models import ExhibitState, SubmissionSource
from app.modules.identity.models import Laboratory, Role
from app.modules.receipt import service as receipts
from tests.casework import accepted, register


@pytest.mark.urs("WF-02.01", "WF-02.02", "WF-02.03")
def test_register_case_with_subcase(db: Session, staff, lab, setting) -> None:
    case, subcase = register(db, staff["cs1"], lab, setting)
    assert case.case_number.startswith("C") and subcase.subcase_number.startswith("LAB")
    assert subcase.case_id == case.id and subcase.laboratory_id == lab.id
    event = audit.history(db, "case", case.id)[0]
    assert event.action == "case.registered"
    assert event.after["submitter_name"] == "SSgt Tan"
    assert event.after["investigating_officer_name"] == "Insp Lee"


@pytest.mark.urs("WF-02.01")
def test_electronic_submission_needs_its_reference(db: Session, staff, lab, setting) -> None:
    with pytest.raises(DomainError, match="submission reference"):
        cases.register_case(
            db,
            actor=staff["cs1"],
            laboratory_id=lab.id,
            client_id=setting.client.id,
            client_reference="X",
            source=SubmissionSource.ELECTRONIC,
            submitter_name="S",
            investigating_officer_name="O",
        )


def test_only_reception_roles_register(db: Session, staff, lab, setting) -> None:
    with pytest.raises(PermissionDenied):
        register(db, staff["dlo1"], lab, setting)


@pytest.mark.urs("WF-01.05")
def test_other_laboratories_cannot_see_the_case(
    db: Session, staff, lab, setting, make_user
) -> None:
    other_lab = Laboratory(code="BIO", name="Biology")
    db.add(other_lab)
    db.flush()
    outsider = make_user(Role.CASE_SCIENTIST, labs=[other_lab])
    case, _ = register(db, staff["cs1"], lab, setting)
    for user in (outsider, staff["codis1"], staff["admin1"]):
        with pytest.raises(NotFound):
            cases.get_case(db, user, case.id)
    assert cases.search_cases(db, outsider) == []
    assert [c.id for c in cases.search_cases(db, staff["dlo1"])] == [case.id]


@pytest.mark.urs("WF-02.02", "WF-19.06")
def test_case_details_corrected_with_reason(db: Session, staff, lab, setting) -> None:
    case, _ = register(db, staff["cs1"], lab, setting)
    cases.update_case_details(
        db,
        actor=staff["cs1"],
        case_id=case.id,
        changes={"submitter_contact": "6999 0000"},
        reason="Submitter gave a new number",
    )
    event = audit.history(db, "case", case.id)[-1]
    assert event.before == {"submitter_contact": "6123 4567"}
    assert event.after == {"submitter_contact": "6999 0000"}
    with pytest.raises(DomainError, match="Nothing"):
        cases.update_case_details(
            db,
            actor=staff["cs1"],
            case_id=case.id,
            changes={"submitter_contact": "6999 0000"},
            reason="again",
        )
    with pytest.raises(DomainError, match="cannot be changed"):
        cases.update_case_details(
            db, actor=staff["cs1"], case_id=case.id, changes={"case_number": "X"}, reason="r"
        )


@pytest.mark.urs("WF-02.04")
def test_each_exhibit_gets_an_identifier_and_barcode(db: Session, staff, lab, setting) -> None:
    from app.modules.items.models import Item

    _, subcase = register(db, staff["cs1"], lab, setting)
    a = cases.add_exhibit(db, actor=staff["cs1"], subcase_id=subcase.id, description="Shirt")
    b = cases.add_exhibit(db, actor=staff["cs1"], subcase_id=subcase.id, description="Knife")
    barcodes = [db.get(Item, e.id).barcode for e in (a, b)]
    assert barcodes[0] != barcodes[1] and all(x.startswith("EX") for x in barcodes)
    assert a.state == ExhibitState.SUBMITTED


@pytest.mark.urs("WF-02.05", "WF-02.06")
def test_exhibits_are_checked_and_accepted_or_rejected_individually(
    db: Session, staff, lab, setting
) -> None:
    cs = staff["cs1"]
    _, subcase = register(db, cs, lab, setting)
    shirt = cases.add_exhibit(db, actor=cs, subcase_id=subcase.id, description="Shirt")
    knife = cases.add_exhibit(db, actor=cs, subcase_id=subcase.id, description="Knife")
    swab = cases.add_exhibit(db, actor=cs, subcase_id=subcase.id, description="Swab")

    with pytest.raises(DomainError, match="Explain the discrepancy"):
        cases.accept_exhibit(
            db,
            actor=cs,
            exhibit_id=shirt.id,
            description_matches=True,
            marking_matches=False,
            seal_intact=True,
        )
    cases.accept_exhibit(
        db,
        actor=cs,
        exhibit_id=shirt.id,
        description_matches=True,
        marking_matches=False,
        seal_intact=True,
        notes="Marking reads A-1 not A1; confirmed with submitter",
    )
    assert shirt.state == ExhibitState.ACCEPTED and shirt.marking_matches is False

    with pytest.raises(DomainError):
        cases.reject_exhibit(db, actor=cs, exhibit_id=knife.id, reason="  ")
    cases.reject_exhibit(
        db,
        actor=cs,
        exhibit_id=knife.id,
        reason="Seal broken; not in sealed packaging",
        seal_intact=False,
    )
    assert knife.state == ExhibitState.REJECTED
    assert knife.rejection_reason == "Seal broken; not in sealed packaging"
    assert swab.state == ExhibitState.SUBMITTED  # unaffected by the others

    cases.reconsider_exhibit(db, actor=cs, exhibit_id=knife.id, reason="Seal re-examined: intact")
    assert knife.state == ExhibitState.SUBMITTED and knife.rejection_reason is None


def test_reconsider_blocked_while_on_a_receipt(db: Session, staff, lab, setting) -> None:
    cs = staff["cs1"]
    _, subcase = register(db, cs, lab, setting)
    shirt = accepted(db, cs, subcase, "Shirt")
    receipts.prepare_receipt(db, actor=cs, subcase_id=subcase.id, exhibit_ids=[shirt.id])
    with pytest.raises(InvalidTransition, match="draft receipt"):
        cases.reconsider_exhibit(db, actor=cs, exhibit_id=shirt.id, reason="changed mind")


@pytest.mark.urs("WF-03.01")
def test_assign_case_scientist_and_reassign_with_reason(db: Session, staff, lab, setting) -> None:
    _, subcase = register(db, staff["slo1"], lab, setting)
    with pytest.raises(PermissionDenied):
        cases.assign_case_scientist(
            db, actor=staff["slo1"], subcase_id=subcase.id, user_id=staff["cs1"].id
        )
    with pytest.raises(DomainError, match="not a case scientist"):
        cases.assign_case_scientist(
            db, actor=staff["rev1"], subcase_id=subcase.id, user_id=staff["dlo1"].id
        )
    cases.assign_case_scientist(
        db, actor=staff["rev1"], subcase_id=subcase.id, user_id=staff["cs1"].id
    )
    assert [s.id for s in cases.my_subcases(db, staff["cs1"])] == [subcase.id]
    with pytest.raises(DomainError, match="reason"):
        cases.assign_case_scientist(
            db, actor=staff["rev1"], subcase_id=subcase.id, user_id=staff["cs2"].id
        )
    cases.assign_case_scientist(
        db,
        actor=staff["rev1"],
        subcase_id=subcase.id,
        user_id=staff["cs2"].id,
        reason="cs1 on leave",
    )
    assert cases.my_subcases(db, staff["cs1"]) == []
    assert [s.id for s in cases.my_subcases(db, staff["cs2"])] == [subcase.id]


@pytest.mark.urs("WF-03.02", "WF-03.03")
def test_examination_is_assigned_or_claimed_separately_from_custody(
    db: Session, staff, lab, setting, received
) -> None:
    from app.modules.custody import service as custody

    subcase, (shirt, knife) = received
    cs, slo = staff["cs1"], staff["slo1"]
    # Only the subcase's Case Scientist may assign; cs1 is not yet assigned.
    with pytest.raises(PermissionDenied):
        cases.assign_examination(db, actor=cs, exhibit_id=shirt.id, user_id=slo.id)
    cases.assign_case_scientist(db, actor=cs, subcase_id=subcase.id, user_id=cs.id)
    cases.assign_examination(db, actor=cs, exhibit_id=shirt.id, user_id=slo.id)
    cases.assign_examination(db, actor=slo, exhibit_id=knife.id)  # claimed
    assert {e.id for e in cases.my_examinations(db, slo)} == {shirt.id, knife.id}
    # Assignment did not move the items: cs1 still holds them.
    assert custody.current(db, shirt.id).to_person_id == cs.id
    with pytest.raises(PermissionDenied):
        cases.assign_examination(db, actor=staff["dlo1"], exhibit_id=shirt.id)


def test_examination_needs_a_received_exhibit(db: Session, staff, lab, setting) -> None:
    _, subcase = register(db, staff["cs1"], lab, setting)
    shirt = accepted(db, staff["cs1"], subcase, "Shirt")
    with pytest.raises(InvalidTransition):
        cases.assign_examination(db, actor=staff["slo1"], exhibit_id=shirt.id)
