import pytest
from fastapi.testclient import TestClient

from app.agents.chat import loop
from tests.fake_llm import FakeLlm, text_message, tool_message


def test_post_message_returns_streaming_placeholder(app_client: TestClient) -> None:
    res = app_client.post("/chat/messages", data={"text": "안녕"})
    assert res.status_code == 200
    assert 'sse-connect="/chat/stream"' in res.text
    assert "안녕" in res.text


def test_stream_sends_deltas_tools_and_done(app_client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        loop,
        "stream_message",
        FakeLlm(
            tool_message(
                "save_user_fact",
                {"category": "skill", "content": "Python", "source": "s", "confirmed": False},
            ),
            text_message("맞아? <b>"),
        ),
    )
    app_client.post("/chat/messages", data={"text": "나는 Python이 제일 익숙해"})
    body = app_client.get("/chat/stream").text
    assert "event: tool" in body
    assert "event: delta\ndata: <span>맞아? &lt;b&gt;</span>" in body  # HTML 이스케이프
    assert body.rstrip().endswith("event: done\ndata:")

    page = app_client.get("/chat").text
    assert "사실 저장: Python" in page
    assert "sse-connect" not in page  # 답이 끝났으니 다시 연결하지 않음


@pytest.mark.usefixtures("db")
def test_stream_without_api_key_shows_notice(app_client: TestClient) -> None:
    app_client.post("/chat/messages", data={"text": "안녕"})
    body = app_client.get("/chat/stream").text
    assert "ANTHROPIC_API_KEY" in body
