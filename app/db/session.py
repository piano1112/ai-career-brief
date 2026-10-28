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


def get_session_factory() -> sessionmaker:
    """스트리밍 응답처럼 요청이 끝난 뒤에도 DB를 써야 하는 곳에서 세션을 직접 열 때 쓴다.

    (FastAPI 의존성으로 받은 세션은 응답이 스트리밍되는 도중에 닫힐 수 있다.)
    테스트에서는 이 의존성을 테스트 DB용 factory로 바꿔 끼운다.
    """
    return SessionLocal
