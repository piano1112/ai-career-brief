"""agent_event 읽기/쓰기 헬퍼. 두 에이전트는 서로 직접 호출하지 않고 이 테이블로만 소통한다."""

from sqlalchemy.orm import Session

from app.db.models import AgentEvent, AgentName, EventPriority


def emit_event(
    db: Session,
    *,
    from_agent: AgentName,
    to_agent: AgentName,
    type: str,
    priority: EventPriority = EventPriority.NORMAL,
    payload: dict | None = None,
) -> AgentEvent:
    event = AgentEvent(
        from_agent=from_agent,
        to_agent=to_agent,
        type=type,
        priority=priority,
        payload=payload or {},
    )
    db.add(event)
    db.flush()  # id를 바로 쓸 수 있게
    return event
