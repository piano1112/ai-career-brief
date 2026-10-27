from app.db.models import SourceType
from app.db.seed_sources import ALL_SOURCES


def test_names_are_unique() -> None:
    names = [s.name for s in ALL_SOURCES]
    assert len(names) == len(set(names))


def test_inactive_sources_record_reason() -> None:
    for s in ALL_SOURCES:
        if not s.active:
            assert s.config.get("inactive_reason"), s.name


def test_active_sources_have_url_and_evidence() -> None:
    for s in ALL_SOURCES:
        if s.active:
            assert s.url.startswith("https://"), s.name
            assert s.config.get("evidence"), s.name


def test_spec_counts() -> None:
    # SPEC 7: 채용 포털 10곳(GS 제외 → 9곳), AI 동향 10곳, 공식 API 1곳
    portals = [s for s in ALL_SOURCES if s.type == SourceType.CAREER_PORTAL]
    assert len(portals) == 9
    assert len(ALL_SOURCES) == 20


def test_active_html_sources_have_link_pattern() -> None:
    for s in ALL_SOURCES:
        if s.type == SourceType.HTML and s.active:
            assert s.config.get("link_pattern"), s.name


def test_access_and_language_filled_or_todo() -> None:
    # 확인 못 한 값은 None으로 두고 config에 TODO를 남긴다 (SPEC_ADDENDUM_01).
    for s in ALL_SOURCES:
        if s.access is None or s.language is None:
            assert "TODO" in str(s.config), s.name
