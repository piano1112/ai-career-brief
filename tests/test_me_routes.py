from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import user_facts
from app.db.models import FactCategory, UserFact


def _fact(db: Session) -> UserFact:
    fact = user_facts.save(
        db,
        category=FactCategory.SKILL,
        content="Python이 제일 익숙하다",
        source="대화",
        confirmed=False,
    )
    db.commit()
    return fact


def test_me_page_shows_unconfirmed_fact(app_client: TestClient, db: Session) -> None:
    _fact(db)
    page = app_client.get("/me").text
    assert "Python이 제일 익숙하다" in page
    assert "미확인" in page and "확인 필요 1개" in page


def test_toggle_confirm(app_client: TestClient, db: Session) -> None:
    fact = _fact(db)
    res = app_client.post(f"/me/facts/{fact.id}/toggle-confirm")
    assert "확인됨" in res.text
    db.refresh(fact)
    assert fact.confirmed is True


def test_edit_creates_confirmed_new_version(app_client: TestClient, db: Session) -> None:
    fact = _fact(db)
    res = app_client.post(f"/me/facts/{fact.id}", data={"content": "Python과 Java가 익숙하다"})
    assert "Python과 Java가 익숙하다" in res.text and "확인됨" in res.text
    current = user_facts.list_current(db)
    assert [(f.content, f.confirmed) for f in current] == [("Python과 Java가 익숙하다", True)]


def test_delete(app_client: TestClient, db: Session) -> None:
    fact = _fact(db)
    assert app_client.post(f"/me/facts/{fact.id}/delete").text == ""
    assert user_facts.list_current(db) == []
    assert app_client.post(f"/me/facts/{fact.id}/toggle-confirm").status_code == 404
