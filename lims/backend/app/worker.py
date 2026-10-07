"""Background worker: `python -m app.worker`."""

import logging
import signal
import time

from app import models  # noqa: F401
from app.core.db import get_sessionmaker
from app.core.jobs import run_next

log = logging.getLogger("lims.worker")
_running = True


def _stop(*_: object) -> None:
    global _running
    _running = False


def main(poll_seconds: float = 2.0) -> None:
    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    log.info("worker started")
    while _running:
        with get_sessionmaker()() as session, session.begin():
            job = run_next(session)
        if job is None:
            time.sleep(poll_seconds)
        else:
            log.info("job %s %s -> %s", job.kind, job.id, job.status)


if __name__ == "__main__":
    main()
