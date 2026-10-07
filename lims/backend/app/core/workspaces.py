"""Role → workspace mapping (WF-01.03)."""

from dataclasses import dataclass

from app.modules.identity.models import Role


@dataclass(frozen=True)
class Workspace:
    key: str
    title: str
    role: Role


WORKSPACES: tuple[Workspace, ...] = (
    Workspace("case-scientist", "Case Scientist", Role.CASE_SCIENTIST),
    Workspace("screening", "Screening Lab", Role.SCREENING_LAB_OFFICER),
    Workspace("dna-lab", "DNA Lab", Role.DNA_LAB_OFFICER),
    Workspace("reviewer", "Reviewer", Role.REVIEWER),
    Workspace("codis", "CODIS", Role.CODIS_SCIENTIST),
    Workspace("admin", "LIMS Admin", Role.LIMS_ADMIN),
)


def workspaces_for(roles: set[Role]) -> list[Workspace]:
    return [w for w in WORKSPACES if w.role in roles]
