"""PostgreSQL 스키마 (SPEC 섹션 4).

설계 메모
- 모든 테이블은 Base를 상속해서 id(uuid) / created_at / updated_at을 자동으로 가진다.
- enum은 Python Enum + PostgreSQL native enum. 잘못된 값이 DB에 들어가는 것을 DB 레벨에서 막는다.
- 구조가 아직 확정되지 않은 값(analysis, payload, config 등)은 JSONB로 둔다.
"""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


def pg_enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    """DB에는 Enum의 '이름'이 아니라 '값'(소문자 문자열)을 저장한다."""
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


def fk(target: str, nullable: bool = False) -> Mapped:
    """FK 컬럼 축약. 예: posting_id = fk("job_posting.id", nullable=True)"""
    return mapped_column(UUID(as_uuid=True), ForeignKey(target), nullable=nullable, index=True)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class FactCategory(enum.StrEnum):
    GOAL = "goal"
    EXPERIENCE = "experience"
    SKILL = "skill"
    PREFERENCE = "preference"
    WEAKNESS_LEARNING = "weakness_learning"
    LIFESTYLE = "lifestyle"


class MessageRole(enum.StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ApplicationStatus(enum.StrEnum):
    CONSIDERING = "considering"
    APPLIED = "applied"
    DOCUMENT_PASSED = "document_passed"
    TEST = "test"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class LogKind(enum.StrEnum):
    EVENT = "event"
    RETRO = "retro"


class DocumentType(enum.StrEnum):
    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    ESSAY_ANSWER = "essay_answer"


class CalendarKind(enum.StrEnum):
    DEADLINE = "deadline"
    TEST = "test"
    INTERVIEW = "interview"
    MANUAL = "manual"


class SourceType(enum.StrEnum):
    RSS = "rss"
    API = "api"
    CAREER_PORTAL = "career_portal"
    # RSS가 없는 사이트의 목록 페이지 (SPEC에 없던 값, docs/decisions.md 010)
    HTML = "html"


class BriefingStatus(enum.StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class BriefingSection(enum.StrEnum):
    SCHEDULE = "schedule"
    AI_TREND = "ai_trend"
    JOBS = "jobs"
    SUGGESTION = "suggestion"
    QUESTION = "question"


class AgentName(enum.StrEnum):
    BACKGROUND = "background"
    CHAT = "chat"


class EventPriority(enum.StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class EventStatus(enum.StrEnum):
    PENDING = "pending"
    PROCESSED = "processed"


# ---------------------------------------------------------------------------
# User Model
# ---------------------------------------------------------------------------


class UserFact(Base):
    """사용자에 대한 사실 하나. 정정 시 삭제하지 않고 superseded_by로 새 fact를 가리킨다."""

    __tablename__ = "user_fact"

    category: Mapped[FactCategory] = mapped_column(pg_enum(FactCategory, "fact_category"))
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    # 에이전트가 추측한 사실은 false로 저장되고, 사용자가 확인하면 true가 된다.
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    superseded_by: Mapped[uuid.UUID | None] = fk("user_fact.id", nullable=True)


class Message(Base):
    """대화 기록. content는 일반 텍스트이거나 Claude의 content block 리스트(tool_use 등)."""

    __tablename__ = "message"

    role: Mapped[MessageRole] = mapped_column(pg_enum(MessageRole, "message_role"))
    content: Mapped[str | list | dict] = mapped_column(JSONB)
    # 예: "main", "feedback:<entry_id>"
    thread: Mapped[str] = mapped_column(Text, default="main", server_default="main", index=True)


# ---------------------------------------------------------------------------
# 수집
# ---------------------------------------------------------------------------


class Source(Base):
    __tablename__ = "source"

    name: Mapped[str] = mapped_column(Text)
    type: Mapped[SourceType] = mapped_column(pg_enum(SourceType, "source_type"))
    url: Mapped[str] = mapped_column(Text)
    tier: Mapped[int] = mapped_column(Integer)  # 1 = 최상위
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # 소스별 설정. 비활성화 사유도 여기에 기록한다 (예: {"inactive_reason": "로그인 필수"}).
    config: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")


class Item(Base):
    """수집된 AI 동향 항목. url unique로 중복 수집을 막는다 (upsert 기준)."""

    __tablename__ = "item"

    source_id: Mapped[uuid.UUID] = fk("source.id")
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, unique=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float)
    # null이면 아직 LLM 분석 전 → 증분 처리 대상
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class JobPosting(Base):
    __tablename__ = "job_posting"

    company_group: Mapped[str] = mapped_column(Text)
    company: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text, unique=True)
    deadline: Mapped[date | None] = mapped_column(Date)
    raw: Mapped[str | None] = mapped_column(Text)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source_id: Mapped[uuid.UUID | None] = fk("source.id", nullable=True)


# ---------------------------------------------------------------------------
# 지원
# ---------------------------------------------------------------------------


class Application(Base):
    __tablename__ = "application"

    posting_id: Mapped[uuid.UUID | None] = fk("job_posting.id", nullable=True)
    company: Mapped[str] = mapped_column(Text)
    position: Mapped[str] = mapped_column(Text)
    status: Mapped[ApplicationStatus] = mapped_column(
        pg_enum(ApplicationStatus, "application_status"),
        default=ApplicationStatus.CONSIDERING,
        server_default=ApplicationStatus.CONSIDERING.value,
    )
    deadline: Mapped[date | None] = mapped_column(Date)
    raw_input: Mapped[str | None] = mapped_column(Text)
    # 직무, 스택, 자격요건, 전형절차, 매칭도, 지원 추천 여부 + 근거
    analysis: Mapped[dict | None] = mapped_column(JSONB)


class ApplicationLog(Base):
    """전형 중 있었던 사건(event)과 사용자의 회고(retro). 결과의 '이유'는 저장하지 않는다."""

    __tablename__ = "application_log"

    application_id: Mapped[uuid.UUID] = fk("application.id")
    stage: Mapped[str] = mapped_column(Text)
    kind: Mapped[LogKind] = mapped_column(pg_enum(LogKind, "log_kind"))
    content: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Document(Base):
    __tablename__ = "document"

    application_id: Mapped[uuid.UUID | None] = fk("application.id", nullable=True)
    type: Mapped[DocumentType] = mapped_column(pg_enum(DocumentType, "document_type"))
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    content: Mapped[str] = mapped_column(Text)


class CalendarEvent(Base):
    __tablename__ = "calendar_event"

    application_id: Mapped[uuid.UUID | None] = fk("application.id", nullable=True)
    title: Mapped[str] = mapped_column(Text)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    kind: Mapped[CalendarKind] = mapped_column(pg_enum(CalendarKind, "calendar_kind"))


# ---------------------------------------------------------------------------
# 브리핑
# ---------------------------------------------------------------------------


class Briefing(Base):
    __tablename__ = "briefing"

    for_date: Mapped[date] = mapped_column(Date, unique=True)
    content: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    html: Mapped[str | None] = mapped_column(Text)
    status: Mapped[BriefingStatus] = mapped_column(
        pg_enum(BriefingStatus, "briefing_status"),
        default=BriefingStatus.DRAFT,
        server_default=BriefingStatus.DRAFT.value,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BriefingEntry(Base):
    __tablename__ = "briefing_entry"

    briefing_id: Mapped[uuid.UUID] = fk("briefing.id")
    section: Mapped[BriefingSection] = mapped_column(pg_enum(BriefingSection, "briefing_section"))
    item_id: Mapped[uuid.UUID | None] = fk("item.id", nullable=True)
    posting_id: Mapped[uuid.UUID | None] = fk("job_posting.id", nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")


class Feedback(Base):
    __tablename__ = "feedback"

    entry_id: Mapped[uuid.UUID] = fk("briefing_entry.id")
    conversation_summary: Mapped[str] = mapped_column(Text)
    # 이 피드백으로 무엇이 바뀌었는지
    outcome: Mapped[str | None] = mapped_column(Text)


# ---------------------------------------------------------------------------
# 에이전트 간 소통 / 운영
# ---------------------------------------------------------------------------


class AgentEvent(Base):
    """두 에이전트는 서로 직접 호출하지 않고 이 테이블로만 소통한다 (양방향 이벤트 큐)."""

    __tablename__ = "agent_event"

    from_agent: Mapped[AgentName] = mapped_column(pg_enum(AgentName, "agent_name"))
    to_agent: Mapped[AgentName] = mapped_column(pg_enum(AgentName, "agent_name"))
    # 예: application_updated, interest_changed, new_posting, deadline_soon, question_for_user
    type: Mapped[str] = mapped_column(Text)
    priority: Mapped[EventPriority] = mapped_column(
        pg_enum(EventPriority, "event_priority"),
        default=EventPriority.NORMAL,
        server_default=EventPriority.NORMAL.value,
    )
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    status: Mapped[EventStatus] = mapped_column(
        pg_enum(EventStatus, "event_status"),
        default=EventStatus.PENDING,
        server_default=EventStatus.PENDING.value,
        index=True,
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LlmUsage(Base):
    """모든 LLM 호출의 토큰/비용 기록 (created_at은 Base에 포함)."""

    __tablename__ = "llm_usage"

    purpose: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
    est_cost_usd: Mapped[float] = mapped_column(Float)
