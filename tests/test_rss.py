from datetime import UTC, datetime

import feedparser

from app.agents.background.collectors.rss import entry_to_item
from app.db.models import SourceAccess

FEED = """<?xml version="1.0"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel><title>t</title>
<item>
  <title>Paid  article</title>
  <link>https://example.com/a</link>
  <description>Public teaser</description>
  <content:encoded><![CDATA[<p>Full body</p>]]></content:encoded>
  <pubDate>Tue, 27 Oct 2026 01:00:00 GMT</pubDate>
</item>
<item><title>No link</title></item>
</channel></rss>"""


def _entries():
    return feedparser.parse(FEED).entries


def test_paid_source_keeps_only_public_summary() -> None:
    item = entry_to_item(_entries()[0], SourceAccess.PAID)
    assert item is not None
    assert item.paywalled is True
    assert item.raw == "Public teaser"
    assert item.title == "Paid article"
    assert item.published_at == datetime(2026, 10, 27, 1, 0, tzinfo=UTC)


def test_free_source_keeps_full_content() -> None:
    item = entry_to_item(_entries()[0], SourceAccess.FREE)
    assert item is not None
    assert item.paywalled is False
    assert "Full body" in item.raw


def test_unknown_access_is_not_marked_paywalled() -> None:
    item = entry_to_item(_entries()[0], None)
    assert item is not None and item.paywalled is False


def test_entry_without_link_is_skipped() -> None:
    assert entry_to_item(_entries()[1], SourceAccess.FREE) is None
