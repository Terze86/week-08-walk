"""Development seed data: `python -m app.seed`. Refuses to run in production.

Creates one laboratory and one account per role, plus a second Case Scientist
and DNA Lab Officer so independent readings and checks can be exercised.
"""

from sqlalchemy import select

from app import models  # noqa: F401
from app.core.config import Environment, get_settings
from app.core.db import get_sessionmaker
from app.modules.identity import service
from app.modules.identity.models import Laboratory, Role, User

DEV_USERS: list[tuple[str, str, list[Role]]] = [
    ("admin1", "Alex Admin", [Role.LIMS_ADMIN]),
    ("cs1", "Casey Scientist", [Role.CASE_SCIENTIST]),
    ("cs2", "Chris Scientist", [Role.CASE_SCIENTIST]),
    ("slo1", "Sam Screening", [Role.SCREENING_LAB_OFFICER]),
    ("dlo1", "Dana DNA", [Role.DNA_LAB_OFFICER]),
    ("dlo2", "Drew DNA", [Role.DNA_LAB_OFFICER]),
    ("rev1", "Robin Reviewer", [Role.REVIEWER]),
    ("codis1", "Cory Codis", [Role.CODIS_SCIENTIST]),
]


def main() -> None:
    if get_settings().environment == Environment.PRODUCTION:
        raise SystemExit("Refusing to seed development accounts in production")
    with get_sessionmaker()() as session, session.begin():
        lab = session.execute(select(Laboratory).filter_by(code="DNA")).scalar_one_or_none()
        if lab is None:
            lab = Laboratory(code="DNA", name="Forensic DNA Laboratory")
            session.add(lab)
            session.flush()
        for username, name, roles in DEV_USERS:
            if session.execute(select(User).filter_by(username=username)).scalar_one_or_none():
                continue
            service.create_user(
                session,
                actor=None,
                username=username,
                display_name=name,
                roles=roles,
                laboratory_ids=[lab.id],
            )
    print("Seeded development laboratory and users:", ", ".join(u for u, _, _ in DEV_USERS))


if __name__ == "__main__":
    main()
