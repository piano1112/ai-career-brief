"""User Model(user_fact) 조작. 대화 에이전트의 도구와 "나에 대해" 화면이 같은 함수를 쓴다.

규칙
- 에이전트가 추측하거나 사용자가 아직 확인하지 않은 사실은 confirmed=False.
- 내용 정정은 기존 행을 고치지 않고 새 행을 만든 뒤 기존 행의 superseded_by가 새 행을 가리킨다
  (이력 보존). '현재 유효한 사실' = superseded_by가 NULL인 행.
- 확인 여부(confirmed)만 바뀌는 것은 내용 변경이 아니므로 그 행을 그대로 고친다.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import FactCategory, UserFact

CATEGORY_LABELS = {
    FactCategory.GOAL: "목표",
    FactCategory.EXPERIENCE: "경험",
    FactCategory.SKILL: "기술",
    FactCategory.PREFERENCE: "선호",
    FactCategory.WEAKNESS_LEARNING: "약점·배우는 중",
    FactCategory.LIFESTYLE: "생활",
}


class FactNotFoundError(ValueError):
    pass


def list_current(db: Session, category: FactCategory | None = None) -> list[UserFact]:
    query = select(UserFact).where(UserFact.superseded_by.is_(None))
    if category is not None:
        query = query.where(UserFact.category == category)
    return list(db.scalars(query.order_by(UserFact.category, UserFact.created_at)))


def get_current(db: Session, fact_id: uuid.UUID) -> UserFact:
    fact = db.get(UserFact, fact_id)
    if fact is None or fact.superseded_by is not None:
        raise FactNotFoundError(f"현재 유효한 사실이 아닙니다: {fact_id}")
    return fact


def save(
    db: Session, *, category: FactCategory, content: str, source: str, confirmed: bool
) -> UserFact:
    fact = UserFact(category=category, content=content.strip(), source=source, confirmed=confirmed)
    db.add(fact)
    db.flush()
    return fact


def update(
    db: Session, fact_id: uuid.UUID, *, content: str, confirmed: bool, source: str
) -> UserFact:
    """내용이 바뀌면 새 버전을 만들고, 확인 여부만 바뀌면 그 자리에서 고친다.

    현재 유효한 버전을 돌려준다.
    """
    old = get_current(db, fact_id)
    content = content.strip()
    if content == old.content:
        old.confirmed = confirmed
        db.flush()
        return old

    new = save(db, category=old.category, content=content, source=source, confirmed=confirmed)
    old.superseded_by = new.id
    db.flush()
    return new


def delete(db: Session, fact_id: uuid.UUID) -> None:
    """사용자가 지운 사실은 이전 버전(정정 이력)까지 함께 지운다.

    정정 이력은 '고쳐진 사실'을 위해 남기는 것이고, 사실 자체가 틀렸다면 이력도 의미가 없다.
    """
    chain = [get_current(db, fact_id)]
    while True:
        previous = db.scalar(select(UserFact).where(UserFact.superseded_by == chain[-1].id))
        if previous is None:
            break
        chain.append(previous)
    # 가장 오래된 버전부터 지워야 FK(superseded_by)가 깨지지 않는다.
    for fact in reversed(chain):
        db.delete(fact)
        db.flush()
