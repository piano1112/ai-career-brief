"""대화 에이전트의 시스템 프롬프트와 매 턴 덧붙이는 <context> 블록.

왜 사실 요약을 시스템 프롬프트가 아니라 사용자 턴에 붙이나 (decisions 011):
Claude Opus 5.5는 이전 턴의 thinking 블록을 다시 보낼 때 system·tools·이전 메시지가
처음과 바이트 단위로 같아야 한다. 매 턴 시스템 프롬프트를 바꾸면 요청이 거부되거나
캐시가 깨진다. 그래서 시스템 프롬프트는 고정하고, 바뀌는 정보(날짜, 확인된 사실)는
바뀌었을 때만 새 사용자 메시지 앞에 <context> 블록으로 덧붙인다 (append-only).
"""

from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import user_facts
from app.db.models import Application, ApplicationStatus

CONTEXT_TAG = "<context>"

# 프롬프트는 코드와 분리해 마크다운 파일로 둔다 (읽고 고치기 쉽게). 서버 시작 시 한 번 읽는다.
SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.md").read_text(encoding="utf-8").strip()

WEEKDAYS = "월화수목금토일"
ACTIVE_STATUSES = [
    ApplicationStatus.CONSIDERING,
    ApplicationStatus.APPLIED,
    ApplicationStatus.DOCUMENT_PASSED,
    ApplicationStatus.TEST,
    ApplicationStatus.INTERVIEW,
]


def build_context(db: Session, now: datetime) -> str:
    lines = [CONTEXT_TAG, f"오늘: {now:%Y-%m-%d} ({WEEKDAYS[now.weekday()]})"]

    facts = user_facts.list_current(db)
    confirmed = [f for f in facts if f.confirmed]
    if confirmed:
        lines.append("확인된 사실:")
        for fact in confirmed:
            label = user_facts.CATEGORY_LABELS[fact.category]
            lines.append(f"- [{label}] {fact.content}")
    else:
        lines.append("확인된 사실: 아직 없음")
    unconfirmed = len(facts) - len(confirmed)
    if unconfirmed:
        lines.append(f"(사용자가 아직 확인하지 않은 사실 {unconfirmed}개 → list_user_facts로 조회)")

    applications = db.scalars(
        select(Application).where(Application.status.in_(ACTIVE_STATUSES))
    ).all()
    if applications:
        lines.append("진행 중인 지원:")
        for app in applications:
            deadline = f", 마감 {app.deadline}" if app.deadline else ""
            lines.append(f"- {app.company} {app.position} ({app.status.value}{deadline})")

    lines.append("</context>")
    return "\n".join(lines)
