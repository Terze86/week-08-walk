import pytest

from app.core import sod
from app.core.errors import SeparationOfDutiesViolation
from app.modules.identity.models import Role


def test_two_readings_need_two_scientists(staff) -> None:
    sod.require_different_people(
        sod.INDEPENDENT_PROFILE_READERS, [staff["cs1"].id, staff["cs2"].id]
    )
    with pytest.raises(SeparationOfDutiesViolation) as exc:
        sod.require_different_people(
            sod.INDEPENDENT_PROFILE_READERS, [staff["cs1"].id, staff["cs1"].id]
        )
    assert exc.value.rule == "SOD-READERS"


def test_independent_check_needs_a_different_officer(staff) -> None:
    sod.require_different_people(
        sod.INDEPENDENT_EXTRACTION_CHECK, [staff["dlo1"].id, staff["dlo2"].id]
    )
    with pytest.raises(SeparationOfDutiesViolation):
        sod.require_different_people(
            sod.INDEPENDENT_EXTRACTION_CHECK, [staff["dlo1"].id, staff["dlo1"].id]
        )


def test_only_the_designated_person_may_act(staff) -> None:
    sod.require_designated_person(sod.HANDOVER_RECEIVER_ACCEPTS, staff["dlo1"], staff["dlo1"].id)
    with pytest.raises(SeparationOfDutiesViolation):
        sod.require_designated_person(
            sod.HANDOVER_RECEIVER_ACCEPTS, staff["dlo2"], staff["dlo1"].id
        )
    with pytest.raises(SeparationOfDutiesViolation):
        sod.require_designated_person(sod.FINAL_SIGNOFF_TECH_REVIEWER, staff["rev1"], None)


@pytest.mark.urs("WF-19.04")
def test_admin_rights_never_substitute_for_a_scientific_role(staff) -> None:
    sod.require_scientific_role(
        sod.ADMIN_NO_SCIENTIFIC_DECISIONS, staff["cs1"], Role.CASE_SCIENTIST
    )
    with pytest.raises(SeparationOfDutiesViolation):
        sod.require_scientific_role(sod.ADMIN_NO_SCIENTIFIC_DECISIONS, staff["admin1"])
    with pytest.raises(SeparationOfDutiesViolation):
        sod.require_scientific_role(
            sod.ADMIN_NO_SCIENTIFIC_DECISIONS, staff["admin1"], Role.LIMS_ADMIN
        )


def test_every_rule_cites_requirements() -> None:
    assert all(rule.urs for rule in sod.ALL_RULES)
    assert len({rule.id for rule in sod.ALL_RULES}) == len(sod.ALL_RULES)
