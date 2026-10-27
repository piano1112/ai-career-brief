"""더미 job (Milestone 1): 스케줄러가 돌고 있고 DB에 연결되는지 주기적으로 확인한다."""

import logging

from sqlalchemy import text

from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def heartbeat() -> None:
    try:
        with SessionLocal() as session:
            db_now = session.execute(text("SELECT now()")).scalar_one()
        logger.info("heartbeat ok — db now() = %s", db_now)
    except Exception:
        # DB가 잠깐 죽어도 worker 프로세스는 계속 살아 있어야 한다 (다음 주기에 재시도).
        logger.exception("heartbeat failed — DB에 연결할 수 없습니다")
