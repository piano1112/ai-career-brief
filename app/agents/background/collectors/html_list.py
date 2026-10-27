"""RSS가 없는 사이트의 '목록 페이지' HTML에서 기사 링크를 뽑는다 (LLM 없이 일반 코드).

사이트마다 CSS 선택자를 짜는 대신, 두 가지 규칙만 쓴다:
  1. 링크 경로가 소스별 정규식(config["link_pattern"])과 맞을 것  예: r"^/news/[^/]+$"
  2. 링크 텍스트(제목)가 충분히 길 것 → "Product", "Policy" 같은 카테고리·메뉴 링크 제외

→ 사이트 디자인이 바뀌어도 URL 규칙만 그대로면 계속 동작한다.
한계: 자바스크립트로 목록을 그리는 페이지는 HTML에 링크가 없다 → Playwright 필요 (M5).
"""

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

DEFAULT_MIN_TITLE_LEN = 15


@dataclass
class FoundLink:
    url: str
    title: str


def _link_title(anchor) -> tuple[str, bool]:  # anchor: bs4 Tag
    """링크 텍스트와 '제목 태그에서 나왔는지' 여부.

    카드형 링크는 제목+요약이 한 <a> 안에 있다 → 제목 태그(h1~h4)가 있으면 그것만 쓴다.
    """
    heading = anchor.find(["h1", "h2", "h3", "h4"])
    text = (heading or anchor).get_text(" ")
    return " ".join(text.split()), heading is not None


def extract_links(
    html: str,
    page_url: str,
    link_pattern: str,
    min_title_len: int = DEFAULT_MIN_TITLE_LEN,
) -> list[FoundLink]:
    """페이지에 나온 순서대로, URL 중복 없이 기사 링크를 돌려준다."""
    pattern = re.compile(link_pattern)
    host = urlsplit(page_url).netloc
    found: dict[str, FoundLink] = {}
    from_heading: dict[str, bool] = {}

    for anchor in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        url = urljoin(page_url, anchor["href"]).split("#")[0].split("?")[0]
        parts = urlsplit(url)
        if parts.netloc != host or not pattern.search(parts.path):
            continue
        title, is_heading = _link_title(anchor)
        if len(title) < min_title_len:
            continue
        # 같은 기사가 여러 번 링크되면(이미지 / 제목 / 요약문 링크 등)
        # 제목 태그에서 나온 텍스트를 우선하고, 그 외에는 처음 나온 것을 쓴다.
        if url not in found or (is_heading and not from_heading[url]):
            found[url] = FoundLink(url=url, title=title)
            from_heading[url] = is_heading

    return list(found.values())


def path_prefix_counts(html: str, page_url: str, top: int = 10) -> list[tuple[str, int]]:
    """link_pattern을 정할 때 참고용: 같은 사이트 링크의 경로 앞부분(2단계)별 개수."""
    host = urlsplit(page_url).netloc
    counts: dict[str, int] = {}
    for anchor in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        parts = urlsplit(urljoin(page_url, anchor["href"]))
        if parts.netloc != host:
            continue
        prefix = "/".join(parts.path.split("/")[:3])
        counts[prefix] = counts.get(prefix, 0) + 1
    return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:top]
