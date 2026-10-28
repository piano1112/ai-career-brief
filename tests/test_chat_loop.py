import pytest
from sqlalchemy.orm import Session

from app.agents.chat import loop
from app.db.models import Message, MessageRole, UserFact
from app.llm.client import TextDelta
from tests.fake_llm import FakeLlm, text_message, tool_message

THREAD = "main"
SAVE_INPUT = {
    "category": "skill",
    "content": "Python이 제일 익숙하다",
    "source": "2026-10-28 대화",
    "confirmed": False,
}


def _use(monkeypatch: pytest.MonkeyPatch, fake: FakeLlm) -> FakeLlm:
    monkeypatch.setattr(loop, "stream_message", fake)
    return fake


def test_spec_m2_scenario_creates_unconfirmed_fact(db: Session, monkeypatch) -> None:
    """SPEC M2 완료 기준: '나는 Python이 제일 익숙해' → 미확인 user_fact 생성."""
    fake = _use(
        monkeypatch,
        FakeLlm(
            tool_message("save_user_fact", SAVE_INPUT),
            text_message("Python이 제일 익숙하다고 이해했는데 맞아?"),
        ),
    )
    loop.add_user_message(db, THREAD, "나는 Python이 제일 익숙해")
    events = list(loop.run_agent(db, THREAD))

    fact = db.query(UserFact).one()
    assert (fact.content, fact.confirmed) == ("Python이 제일 익숙하다", False)

    roles = [m.role for m in db.query(Message).order_by(Message.seq)]
    assert roles == [
        MessageRole.USER,
        MessageRole.ASSISTANT,
        MessageRole.TOOL,
        MessageRole.ASSISTANT,
    ]

    # 두 번째 요청: tool_result가 role "user"로, 바로 앞 tool_use와 짝지어 전달된다
    second = fake.requests[1]["messages"]
    assert second[-1]["role"] == "user"
    assert second[-1]["content"][0]["tool_use_id"] == second[-2]["content"][0]["id"]

    assert any(isinstance(e, loop.ToolNotice) for e in events)
    assert "".join(e.text for e in events if isinstance(e, TextDelta)).endswith("맞아?")
    assert not loop.needs_reply(db, THREAD)


def test_context_is_added_only_when_changed(db: Session, monkeypatch) -> None:
    _use(monkeypatch, FakeLlm(text_message("안녕"), text_message("응")))
    for text in ["안녕", "또 안녕"]:
        loop.add_user_message(db, THREAD, text)
        list(loop.run_agent(db, THREAD))

    user_messages = db.query(Message).filter_by(role=MessageRole.USER).order_by(Message.seq).all()
    assert len(user_messages[0].content) == 2  # <context> + 본문
    assert len(user_messages[1].content) == 1  # 바뀐 게 없으니 본문만
    # 화면에는 <context>가 보이지 않는다
    assert [i.text for i in loop.display_items(db, THREAD)] == ["안녕", "안녕", "또 안녕", "응"]


def test_refusal_is_not_saved(db: Session, monkeypatch) -> None:
    _use(monkeypatch, FakeLlm(text_message("", stop_reason="refusal")))
    loop.add_user_message(db, THREAD, "질문")
    events = list(loop.run_agent(db, THREAD))
    assert isinstance(events[-1], loop.Notice)
    assert db.query(Message).filter_by(role=MessageRole.ASSISTANT).count() == 0


def test_truncated_tool_call_is_not_executed(db: Session, monkeypatch) -> None:
    truncated = tool_message("save_user_fact", SAVE_INPUT)
    truncated.stop_reason = "max_tokens"
    _use(monkeypatch, FakeLlm(truncated, text_message("다시 할게")))
    loop.add_user_message(db, THREAD, "나는 Python이 제일 익숙해")
    list(loop.run_agent(db, THREAD))

    assert db.query(UserFact).count() == 0
    tool_message_row = db.query(Message).filter_by(role=MessageRole.TOOL).one()
    assert tool_message_row.content[0]["is_error"] is True
