from app.db.models import Base

# SPEC 섹션 4의 테이블 목록
SPEC_TABLES = {
    "user_fact",
    "message",
    "job_posting",
    "application",
    "application_log",
    "document",
    "calendar_event",
    "source",
    "item",
    "briefing",
    "briefing_entry",
    "feedback",
    "agent_event",
    "llm_usage",
}


def test_all_spec_tables_exist() -> None:
    assert set(Base.metadata.tables) == SPEC_TABLES


def test_every_table_has_common_columns() -> None:
    for table in Base.metadata.tables.values():
        assert {"id", "created_at", "updated_at"} <= set(table.columns.keys()), table.name
