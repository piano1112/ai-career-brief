from sqlalchemy.orm import Session

from app import user_facts
from app.db.models import FactCategory, UserFact


def _save(db: Session, content: str = "Python이 제일 익숙하다") -> UserFact:
    return user_facts.save(
        db, category=FactCategory.SKILL, content=content, source="test", confirmed=False
    )


def test_update_only_confirmed_changes_in_place(db: Session) -> None:
    fact = _save(db)
    updated = user_facts.update(db, fact.id, content=fact.content, confirmed=True, source="test2")
    assert updated.id == fact.id
    assert updated.confirmed is True
    assert db.query(UserFact).count() == 1


def test_update_content_keeps_history(db: Session) -> None:
    fact = _save(db)
    new = user_facts.update(
        db, fact.id, content="Java가 제일 익숙하다", confirmed=False, source="s"
    )
    assert new.id != fact.id
    assert fact.superseded_by == new.id
    assert [f.content for f in user_facts.list_current(db)] == ["Java가 제일 익숙하다"]


def test_delete_removes_whole_history(db: Session) -> None:
    fact = _save(db)
    v2 = user_facts.update(db, fact.id, content="v2", confirmed=False, source="s")
    v3 = user_facts.update(db, v2.id, content="v3", confirmed=True, source="s")
    user_facts.delete(db, v3.id)
    assert db.query(UserFact).count() == 0


def test_superseded_fact_is_not_current(db: Session) -> None:
    fact = _save(db)
    user_facts.update(db, fact.id, content="v2", confirmed=False, source="s")
    try:
        user_facts.get_current(db, fact.id)
        raise AssertionError("이전 버전은 현재 사실이 아니어야 함")
    except user_facts.FactNotFoundError:
        pass
