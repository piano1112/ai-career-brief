"""RSS 항목 → item 필드 변환. collect_rss job(M5)이 이 함수를 쓴다.

유료 소스 규칙 (SPEC_ADDENDUM_01):
- access=paid 소스는 RSS가 공개한 제목·공개 요약만 저장하고 paywalled=True.
- RSS에 본문(content)이 들어 있어도 유료 소스면 저장하지 않는다.
- 본문을 얻으려고 원문 페이지·아카이브·캐시·미러를 찾아가지 않는다 (페이월 우회 금지).
"""

import calendar
from dataclasses import dataclass
from datetime import UTC, datetime

from app.db.models import SourceAccess


@dataclass
class RssItem:
    url: str
    title: str
    published_at: datetime | None
    raw: str  # 저장할 원문: 무료면 본문(없으면 요약), 유료면 공개 요약만
    paywalled: bool


def _published_at(entry) -> datetime | None:  # entry: feedparser entry
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed is None:
        return None
    # feedparser는 UTC 기준 time.struct_time을 준다.
    return datetime.fromtimestamp(calendar.timegm(parsed), tz=UTC)


def entry_to_item(entry, access: SourceAccess | None) -> RssItem | None:
    """링크가 없는 항목은 저장할 수 없으므로(url이 unique 키) None."""
    url = entry.get("link")
    if not url:
        return None

    summary = entry.get("summary", "")
    paywalled = access == SourceAccess.PAID
    if paywalled:
        raw = summary
    else:
        contents = entry.get("content") or []
        raw = contents[0].get("value", "") if contents else summary

    return RssItem(
        url=url,
        title=" ".join(entry.get("title", "").split()),
        published_at=_published_at(entry),
        raw=raw,
        paywalled=paywalled,
    )
