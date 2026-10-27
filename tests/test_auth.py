import pytest
from fastapi.testclient import TestClient

from tests.conftest import TEST_PASSWORD

PAGES = ["/", "/chat", "/applications", "/calendar", "/me"]


def test_healthz_is_public(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


@pytest.mark.parametrize("path", PAGES)
def test_pages_redirect_to_login_when_logged_out(client: TestClient, path: str) -> None:
    res = client.get(path, follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/login"


def test_htmx_request_gets_hx_redirect(client: TestClient) -> None:
    res = client.get("/chat", headers={"HX-Request": "true"}, follow_redirects=False)
    assert res.status_code == 401
    assert res.headers["HX-Redirect"] == "/login"


def test_wrong_password_is_rejected(client: TestClient) -> None:
    res = client.post("/login", data={"username": "me", "password": "nope"})
    assert res.status_code == 401
    assert client.get("/", follow_redirects=False).status_code == 303


def test_login_then_logout(client: TestClient) -> None:
    res = client.post(
        "/login", data={"username": "me", "password": TEST_PASSWORD}, follow_redirects=False
    )
    assert res.status_code == 303
    assert client.get("/", follow_redirects=False).status_code == 200

    client.post("/logout")
    assert client.get("/", follow_redirects=False).status_code == 303


@pytest.mark.parametrize("path", PAGES)
def test_pages_render_with_sidebar(logged_in_client: TestClient, path: str) -> None:
    res = logged_in_client.get(path)
    assert res.status_code == 200
    for label in ["브리핑", "대화", "지원현황", "캘린더", "나에 대해"]:
        assert label in res.text
