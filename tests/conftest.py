import os

import pytest
from fastapi.testclient import TestClient

from app.auth import hash_password

TEST_PASSWORD = "test-password"

# app.main을 import하기 전에 설정해야 한다 (Settings가 import 시점에 읽힘).
os.environ["SESSION_SECRET"] = "test-secret"
os.environ["ADMIN_USERNAME"] = "me"
os.environ["ADMIN_PASSWORD_HASH"] = hash_password(TEST_PASSWORD)


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


@pytest.fixture
def logged_in_client(client: TestClient) -> TestClient:
    client.post("/login", data={"username": "me", "password": TEST_PASSWORD})
    return client
