import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.auth import hash_password

TEST_PASSWORD = "test-password"
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://brief:brief@localhost:5432/brief_test"
)

# app.main을 import하기 전에 설정해야 한다 (Settings가 import 시점에 읽힘).
os.environ["SESSION_SECRET"] = "test-secret"
os.environ["ADMIN_USERNAME"] = "me"
os.environ["ADMIN_PASSWORD_HASH"] = hash_password(TEST_PASSWORD)
# 테스트가 실제 Claude API를 부르지 않게 키를 비운다. (Claude 호출은 각 테스트에서 가짜로 바꿔 끼움)
os.environ["ANTHROPIC_API_KEY"] = ""


# ---------------------------------------------------------------------------
# DB: 별도 테스트 DB(brief_test)를 쓴다. 연결이 안 되면 DB 테스트는 건너뛴다.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def db_factory() -> sessionmaker:
    from app.db.models import Base

    engine = create_engine(TEST_DATABASE_URL)
    try:
        engine.connect().close()
    except OperationalError:
        pytest.skip(f"테스트 DB에 연결할 수 없음: {TEST_DATABASE_URL}")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def db(db_factory: sessionmaker) -> Session:
    from app.db.models import Base

    with db_factory() as session:
        yield session
    # 테스트마다 모든 테이블을 비운다.
    with db_factory() as session:
        tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
        session.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
        session.commit()


# ---------------------------------------------------------------------------
# 웹
# ---------------------------------------------------------------------------
@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


@pytest.fixture
def logged_in_client(client: TestClient) -> TestClient:
    client.post("/login", data={"username": "me", "password": TEST_PASSWORD})
    return client


@pytest.fixture
def app_client(db: Session, db_factory: sessionmaker) -> TestClient:
    """테스트 DB를 쓰는 로그인된 클라이언트."""
    from app.db.session import get_db, get_session_factory
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_session_factory] = lambda: db_factory
    test_client = TestClient(app)
    test_client.post("/login", data={"username": "me", "password": TEST_PASSWORD})
    yield test_client
    app.dependency_overrides.clear()
