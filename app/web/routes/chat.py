"""채팅 화면.

흐름 (HTMX + Server-Sent Events)
  1. 폼 제출 → POST /chat/messages: 사용자 메시지를 저장하고, 화면에 붙일 조각을 돌려준다.
     조각 안의 답변 칸에 sse-connect="/chat/stream"이 있어서 브라우저가 바로 스트림에 연결한다.
  2. GET /chat/stream: 에이전트 루프를 돌리면서 글자 조각(delta), 도구 사용(tool), 안내(notice)를
     SSE 이벤트로 보낸다. 끝나면 done 이벤트 → 브라우저가 연결을 닫는다.
"""

import html
import logging
from collections.abc import Iterator
from typing import Annotated

import anthropic
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from app.agents.chat import loop
from app.db.session import get_db, get_session_factory
from app.llm.client import LlmNotConfiguredError, TextDelta
from app.web.templating import templates

router = APIRouter()
logger = logging.getLogger(__name__)

THREAD = "main"  # 피드백 스레드(feedback:<entry_id>)는 Milestone 5 이후


@router.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request, db: Annotated[Session, Depends(get_db)]) -> Response:
    return templates.TemplateResponse(
        request,
        "chat.html",
        {
            "items": loop.display_items(db, THREAD),
            # 답이 아직 안 끝난 상태(예: 새로고침)면 답변 칸을 다시 연결한다.
            "pending": loop.needs_reply(db, THREAD),
        },
    )


@router.post("/chat/messages", response_class=HTMLResponse)
def post_message(
    request: Request,
    text: Annotated[str, Form()],
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    text = text.strip()
    if not text:
        return HTMLResponse("")
    loop.add_user_message(db, THREAD, text)
    return templates.TemplateResponse(request, "_chat_turn.html", {"text": text})


def _sse(event: str, data: str) -> str:
    # SSE 형식: 여러 줄 데이터는 줄마다 "data:"를 붙인다. 브라우저가 줄바꿈으로 다시 합친다.
    lines = "".join(f"data: {line}\n" for line in data.split("\n"))
    return f"event: {event}\n{lines}\n"


def _events(session_factory: sessionmaker) -> Iterator[str]:
    with session_factory() as db:
        try:
            for event in loop.run_agent(db, THREAD):
                if isinstance(event, TextDelta):
                    yield _sse("delta", f"<span>{html.escape(event.text)}</span>")
                elif isinstance(event, loop.ToolNotice):
                    yield _sse("tool", _badge("🔧 " + event.text, "bg-slate-100 text-slate-500"))
                else:
                    yield _sse("notice", _badge("⚠️ " + event.text, "bg-amber-50 text-amber-700"))
        except LlmNotConfiguredError as e:
            yield _sse("notice", _badge(f"⚠️ {e}", "bg-amber-50 text-amber-700"))
        except anthropic.APIError as e:
            logger.exception("Claude API 오류")
            message = f"⚠️ Claude API 오류: {type(e).__name__}. 잠시 후 다시 시도해 주세요."
            yield _sse("notice", _badge(message, "bg-red-50 text-red-700"))
    yield _sse("done", "")


def _badge(text: str, colors: str) -> str:
    return f'<div class="my-1 rounded-md px-2 py-1 text-xs {colors}">{html.escape(text)}</div>'


@router.get("/chat/stream")
def stream(
    session_factory: Annotated[sessionmaker, Depends(get_session_factory)],
) -> StreamingResponse:
    return StreamingResponse(
        _events(session_factory),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
