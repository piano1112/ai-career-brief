"""DB 엔진과 세션.

web(FastAPI)은 async지만 DB 접근은 동기 SQLAlchemy를 쓴다.
→ 1인용 앱이라 동시 요청이 거의 없고, 동기 코드가 읽고 디버깅하기 훨씬 쉽다.
  (FastAPI는 `def` 라우트를 스레드풀에서 실행하므로 이벤트 루프를 막지 않는다.)
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI 의존성: 요청마다 세션을 열고 끝나면 닫는다."""
    with SessionLocal() as session:
        yield session
