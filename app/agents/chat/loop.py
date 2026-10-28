"""대화 에이전트 루프 (SPEC 5.2). Claude API tool use를 직접 돌리는 수동 루프.

한 턴의 흐름
  1. add_user_message(): 사용자 메시지를 저장한다. (<context>가 바뀌었으면 앞에 붙임)
  2. run_agent(): Claude에 대화 기록 전체를 보내고 답을 스트리밍한다.
     Claude가 도구를 쓰겠다고 하면(tool_use) → 도구 실행 → 결과(tool_result) 저장
     → 다시 Claude 호출.
     도구 호출이 없으면 끝.

대화 기록 규칙 (decisions 011)
- append-only: 저장된 메시지는 고치거나 지우지 않는다. (thinking 블록 유효성 + 프롬프트 캐시)
- Claude가 준 content 블록(thinking 포함)은 받은 그대로 저장하고 그대로 다시 보낸다.
- DB의 role "tool"은 tool_result 묶음이다. API에는 role "user"로 보낸다.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.chat import prompts, tools
from app.config import get_settings
from app.db.models import Message, MessageRole
from app.llm.client import Final, TextDelta, stream_message

MAX_TOOL_ROUNDS = 8  # 한 턴에서 도구 호출이 끝없이 반복되는 것을 막는다


@dataclass
class ToolNotice:
    text: str  # 화면에 보여줄 도구 사용 설명


@dataclass
class Notice:
    text: str  # 거절·잘림 같은 안내


ChatEvent = TextDelta | ToolNotice | Notice


def _messages(db: Session, thread: str) -> list[Message]:
    return list(db.scalars(select(Message).where(Message.thread == thread).order_by(Message.seq)))


def _save(db: Session, thread: str, role: MessageRole, content: list[dict]) -> None:
    db.add(Message(thread=thread, role=role, content=content))
    db.commit()


def _last_context(messages: list[Message]) -> str | None:
    for message in reversed(messages):
        if message.role != MessageRole.USER:
            continue
        for block in message.content:
            if block.get("type") == "text" and block["text"].startswith(prompts.CONTEXT_TAG):
                return block["text"]
    return None


def add_user_message(db: Session, thread: str, text: str) -> None:
    now = datetime.now(ZoneInfo(get_settings().tz))
    context = prompts.build_context(db, now)
    blocks = []
    # 날짜나 확인된 사실이 바뀌었을 때만 새 <context>를 붙인다 (매번 붙이면 토큰 낭비)
    if context != _last_context(_messages(db, thread)):
        blocks.append({"type": "text", "text": context})
    blocks.append({"type": "text", "text": text})
    _save(db, thread, MessageRole.USER, blocks)


def needs_reply(db: Session, thread: str) -> bool:
    """마지막 메시지가 사용자 메시지나 도구 결과면 Claude가 답할 차례다."""
    messages = _messages(db, thread)
    return bool(messages) and messages[-1].role != MessageRole.ASSISTANT


def _api_messages(messages: list[Message]) -> list[dict]:
    return [
        {
            "role": "assistant" if m.role == MessageRole.ASSISTANT else "user",
            "content": m.content,
        }
        for m in messages
    ]


def run_agent(db: Session, thread: str) -> Iterator[ChatEvent]:
    for _ in range(MAX_TOOL_ROUNDS):
        if not needs_reply(db, thread):
            return

        final = None
        for event in stream_message(
            purpose="chat",
            system=prompts.SYSTEM_PROMPT,
            messages=_api_messages(_messages(db, thread)),
            tools=tools.TOOL_DEFINITIONS,
        ):
            if isinstance(event, Final):
                final = event.message
            else:
                yield event

        if final.stop_reason == "refusal":
            # 거절된 응답은 저장하지 않는다 (부분 출력은 완성된 답이 아님).
            yield Notice(
                "이 요청에는 답할 수 없다는 응답을 받았어요. 표현을 바꿔서 다시 말해 줄래요?"
            )
            return

        # by_alias: fallback 블록의 "from" 필드 등 API 원래 이름으로 저장
        content = [
            b.model_dump(mode="json", by_alias=True, exclude_none=True) for b in final.content
        ]
        _save(db, thread, MessageRole.ASSISTANT, content)

        tool_uses = [b for b in final.content if b.type == "tool_use"]
        if not tool_uses:
            if final.stop_reason == "max_tokens":
                yield Notice("답이 길이 제한에 걸려 잘렸어요.")
            return

        results = []
        for block in tool_uses:
            if final.stop_reason == "max_tokens":
                # 잘린 도구 입력은 실행하지 않는다.
                # 그래도 tool_use마다 결과는 있어야 대화 기록이 유효하다.
                result = tools.ToolResult('{"error": "입력이 잘려서 실행하지 않음"}', is_error=True)
            else:
                result = tools.run_tool(db, block.name, block.input)
                yield ToolNotice(tools.describe(block.name, block.input))
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result.content,
                    "is_error": result.is_error,
                }
            )
        # 도구가 바꾼 DB 내용과 tool_result를 한 번에 커밋한다.
        _save(db, thread, MessageRole.TOOL, results)

    yield Notice("도구 호출이 너무 많아서 여기서 멈췄어요.")


@dataclass
class DisplayItem:
    role: str  # "user" | "assistant" | "tool"
    text: str


def display_items(db: Session, thread: str) -> list[DisplayItem]:
    """채팅 화면에 보여줄 내용. <context>, thinking, tool_result 원문은 숨긴다."""
    items = []
    for message in _messages(db, thread):
        if message.role == MessageRole.TOOL:
            continue
        for block in message.content:
            if block.get("type") == "text":
                if block["text"].startswith(prompts.CONTEXT_TAG):
                    continue
                items.append(DisplayItem(message.role.value, block["text"]))
            elif block.get("type") == "tool_use":
                items.append(DisplayItem("tool", tools.describe(block["name"], block["input"])))
    return items
