"""대화 에이전트가 쓰는 도구 (SPEC 5.2, Milestone 2).

TOOL_DEFINITIONS: Claude에게 보내는 도구 설명(JSON Schema)
run_tool(): Claude가 요청한 도구를 실제로 실행하고, 결과를 문자열로 돌려준다.

strict=True: Claude가 스키마에 맞는 인자만 보내도록 보장. 단 emit_event의 payload처럼
자유 형식 객체가 있는 도구는 strict를 쓸 수 없어서 직접 검증한다.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app import user_facts
from app.config import get_settings
from app.db.models import AgentName, EventPriority, FactCategory
from app.events import emit_event

CATEGORIES = [c.value for c in FactCategory]

TOOL_DEFINITIONS: list[dict] = [
    {
        "name": "save_user_fact",
        "description": (
            "사용자에 대한 새 사실 하나를 저장한다. 사용자가 확인하기 전에는 confirmed=false."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": CATEGORIES},
                "content": {"type": "string", "description": "짧고 구체적인 문장 하나"},
                "source": {"type": "string", "description": '예: "2026-10-28 대화"'},
                "confirmed": {"type": "boolean"},
            },
            "required": ["category", "content", "source", "confirmed"],
            "additionalProperties": False,
        },
    },
    {
        "name": "update_user_fact",
        "description": (
            "저장된 사실을 고치거나 확인 처리한다. 내용이 바뀌면 새 버전이 생기고 이전 버전은 "
            "이력으로 남는다. 내용을 바꾸지 않을 때는 content에 현재 내용을 그대로 넣는다."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "list_user_facts가 돌려준 id"},
                "content": {"type": "string"},
                "confirmed": {"type": "boolean"},
            },
            "required": ["id", "content", "confirmed"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_user_facts",
        "description": "현재 유효한 사실 목록(id 포함)을 조회한다. category='all'이면 전체.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"category": {"type": "string", "enum": ["all", *CATEGORIES]}},
            "required": ["category"],
            "additionalProperties": False,
        },
    },
    {
        "name": "emit_event",
        "description": (
            "백그라운드 에이전트(수집·브리핑 담당)에게 이벤트를 보낸다. "
            "type 예: interest_changed, application_updated"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "priority": {"type": "string", "enum": [p.value for p in EventPriority]},
                "payload": {"type": "object", "description": "이벤트 내용 (자유 형식)"},
            },
            "required": ["type", "priority", "payload"],
        },
    },
]


@dataclass
class ToolResult:
    content: str  # Claude에게 돌려줄 결과 (JSON 문자열)
    is_error: bool = False


def describe(name: str, tool_input: dict) -> str:
    """채팅 화면에 보여줄 한 줄 설명."""
    if name == "save_user_fact":
        return f"사실 저장: {tool_input.get('content', '')}"
    if name == "update_user_fact":
        state = "확인됨" if tool_input.get("confirmed") else "미확인"
        return f"사실 수정 ({state}): {tool_input.get('content', '')}"
    if name == "list_user_facts":
        return "저장된 사실 조회"
    if name == "emit_event":
        return f"백그라운드에 알림: {tool_input.get('type', '')}"
    return name


def _ok(data: dict | list) -> ToolResult:
    return ToolResult(json.dumps(data, ensure_ascii=False))


def _error(message: str) -> ToolResult:
    return ToolResult(json.dumps({"error": message}, ensure_ascii=False), is_error=True)


def _fact_dict(fact) -> dict:
    return {
        "id": str(fact.id),
        "category": fact.category.value,
        "content": fact.content,
        "confirmed": fact.confirmed,
        "source": fact.source,
    }


def _today_source() -> str:
    return f"{datetime.now(ZoneInfo(get_settings().tz)):%Y-%m-%d} 대화"


def run_tool(db: Session, name: str, tool_input: dict) -> ToolResult:
    """도구 실행.

    입력이 잘못되면 예외 대신 is_error 결과를 돌려줘서 Claude가 고쳐서 다시 부르게 한다.
    """
    try:
        if name == "save_user_fact":
            fact = user_facts.save(
                db,
                category=FactCategory(tool_input["category"]),
                content=tool_input["content"],
                source=tool_input["source"] or _today_source(),
                confirmed=bool(tool_input["confirmed"]),
            )
            return _ok(_fact_dict(fact))

        if name == "update_user_fact":
            fact = user_facts.update(
                db,
                uuid.UUID(tool_input["id"]),
                content=tool_input["content"],
                confirmed=bool(tool_input["confirmed"]),
                source=_today_source(),
            )
            return _ok(_fact_dict(fact))

        if name == "list_user_facts":
            category = tool_input["category"]
            facts = user_facts.list_current(
                db, None if category == "all" else FactCategory(category)
            )
            return _ok([_fact_dict(f) for f in facts])

        if name == "emit_event":
            if not isinstance(tool_input.get("payload"), dict):
                return _error("payload는 객체여야 합니다")
            event = emit_event(
                db,
                from_agent=AgentName.CHAT,
                to_agent=AgentName.BACKGROUND,
                type=str(tool_input["type"]),
                priority=EventPriority(tool_input["priority"]),
                payload=tool_input["payload"],
            )
            return _ok({"event_id": str(event.id), "status": "pending"})

        return _error(f"알 수 없는 도구: {name}")
    except (KeyError, ValueError) as e:  # 잘못된 enum 값·uuid, 없는 사실 id 등
        return _error(f"{type(e).__name__}: {e}")
