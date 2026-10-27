"""백그라운드 에이전트 엔트리포인트 (worker 컨테이너).  실행: python worker.py"""

import logging

from app.agents.background.scheduler import build_scheduler
from app.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("worker")


def main() -> None:
    scheduler = build_scheduler()
    logger.info("worker started (timezone=%s)", get_settings().tz)
    for job in scheduler.get_jobs():
        logger.info("job registered: %s (%s)", job.id, job.trigger)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("worker stopped")


if __name__ == "__main__":
    main()
