"""'나에 대해' 화면: 에이전트가 알게 된 사실(user_fact)을 카테고리별로 보고 직접 고친다.

각 사실 카드는 HTMX로 그 카드만 바꿔 끼운다 (확인 토글 / 수정 / 삭제).
사용자가 직접 고친 내용은 사용자가 쓴 것이므로 confirmed=True로 저장한다.
"""

import uuid
from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app import user_facts
from app.config import get_settings
from app.db.models import FactCategory, UserFact
from app.db.session import get_db
from app.web.templating import templates

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]


# 템플릿에서 카테고리 아이콘을 쓰기 위한 표
CATEGORY_ICONS = {
    FactCategory.GOAL: "🎯",
    FactCategory.EXPERIENCE: "🛠️",
    FactCategory.SKILL: "💡",
    FactCategory.PREFERENCE: "❤️",
    FactCategory.WEAKNESS_LEARNING: "📚",
    FactCategory.LIFESTYLE: "🌙",
}
templates.env.globals["category_icons"] = {
    user_facts.CATEGORY_LABELS[c]: icon for c, icon in CATEGORY_ICONS.items()
}


def _current_or_404(db: Session, fact_id: uuid.UUID) -> UserFact:
    try:
        return user_facts.get_current(db, fact_id)
    except user_facts.FactNotFoundError as e:
        raise HTTPException(404, str(e)) from e


def _card(request: Request, fact: UserFact) -> Response:
    return templates.TemplateResponse(request, "_fact_card.html", {"fact": fact})


@router.get("/me", response_class=HTMLResponse)
def me_page(request: Request, db: DB) -> Response:
    facts = user_facts.list_current(db)
    groups = [
        (label, [f for f in facts if f.category == category])
        for category, label in user_facts.CATEGORY_LABELS.items()
    ]
    return templates.TemplateResponse(
        request,
        "me.html",
        {
            "groups": groups,
            "total": len(facts),
            "unconfirmed": sum(not f.confirmed for f in facts),
        },
    )


@router.post("/me/facts/{fact_id}/toggle-confirm", response_class=HTMLResponse)
def toggle_confirm(request: Request, fact_id: uuid.UUID, db: DB) -> Response:
    fact = _current_or_404(db, fact_id)
    fact.confirmed = not fact.confirmed
    db.commit()
    return _card(request, fact)


@router.get("/me/facts/{fact_id}/card", response_class=HTMLResponse)
def card(request: Request, fact_id: uuid.UUID, db: DB) -> Response:
    return _card(request, _current_or_404(db, fact_id))


@router.get("/me/facts/{fact_id}/edit", response_class=HTMLResponse)
def edit_form(request: Request, fact_id: uuid.UUID, db: DB) -> Response:
    fact = _current_or_404(db, fact_id)
    return templates.TemplateResponse(request, "_fact_edit.html", {"fact": fact})


@router.post("/me/facts/{fact_id}", response_class=HTMLResponse)
def save_edit(
    request: Request, fact_id: uuid.UUID, content: Annotated[str, Form()], db: DB
) -> Response:
    _current_or_404(db, fact_id)
    if not content.strip():
        raise HTTPException(400, "내용이 비어 있습니다")
    today = datetime.now(ZoneInfo(get_settings().tz))
    fact = user_facts.update(
        db, fact_id, content=content, confirmed=True, source=f"{today:%Y-%m-%d} 직접 수정"
    )
    db.commit()
    return _card(request, fact)


@router.post("/me/facts/{fact_id}/delete", response_class=HTMLResponse)
def delete(fact_id: uuid.UUID, db: DB) -> Response:
    _current_or_404(db, fact_id)
    user_facts.delete(db, fact_id)
    db.commit()
    return HTMLResponse("")  # 카드 자리를 빈 내용으로 바꿔서 화면에서 지운다
