import json
import uuid

from sqlalchemy.orm import Session

from app.agents.chat.tools import TOOL_DEFINITIONS, run_tool
from app.db.models import AgentEvent, AgentName


def test_strict_tools_have_closed_schemas() -> None:
    for tool in TOOL_DEFINITIONS:
        if tool.get("strict"):
            schema = tool["input_schema"]
            assert schema["additionalProperties"] is False, tool["name"]
            assert set(schema["required"]) == set(schema["properties"]), tool["name"]


def test_save_list_update_flow(db: Session) -> None:
    saved = run_tool(
        db,
        "save_user_fact",
        {
            "category": "skill",
            "content": "Python이 제일 익숙하다",
            "source": "s",
            "confirmed": False,
        },
    )
    fact = json.loads(saved.content)
    assert saved.is_error is False and fact["confirmed"] is False

    listed = json.loads(run_tool(db, "list_user_facts", {"category": "all"}).content)
    assert [f["id"] for f in listed] == [fact["id"]]

    confirmed = run_tool(
        db, "update_user_fact", {"id": fact["id"], "content": fact["content"], "confirmed": True}
    )
    assert json.loads(confirmed.content)["confirmed"] is True


def test_bad_inputs_return_errors_instead_of_raising(db: Session) -> None:
    bad_category = run_tool(
        db, "save_user_fact", {"category": "x", "content": "c", "source": "s", "confirmed": False}
    )
    assert bad_category.is_error
    missing = run_tool(
        db, "update_user_fact", {"id": str(uuid.uuid4()), "content": "c", "confirmed": True}
    )
    assert missing.is_error
    assert run_tool(db, "unknown_tool", {}).is_error


def test_emit_event_goes_to_background(db: Session) -> None:
    result = run_tool(
        db,
        "emit_event",
        {"type": "interest_changed", "priority": "normal", "payload": {"topic": "AI 에이전트"}},
    )
    assert not result.is_error
    event = db.query(AgentEvent).one()
    assert (event.from_agent, event.to_agent) == (AgentName.CHAT, AgentName.BACKGROUND)
    assert event.payload == {"topic": "AI 에이전트"}
