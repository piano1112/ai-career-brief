"""수집 소스 검증 스크립트.

app/db/seed_sources.py의 각 소스에 대해 확인한다:
  1. robots.txt가 우리 User-Agent의 접근을 허용하는지
  2. HTTP 응답 코드 (리다이렉트 후 최종 URL 포함)
  3. type=rss  → feedparser로 파싱되는지, 항목 수, 최신 항목 날짜
     type=api  → JSON으로 파싱되는지, 항목 수
     career_portal → 응답 크기 (작으면 JS 렌더링이 필요할 가능성 → Playwright)

실행 (네트워크가 열린 환경에서):
    python -m scripts.verify_sources                 # 결과 표 출력
    python -m scripts.verify_sources --write         # docs/sources-verification.md에도 저장
    python -m scripts.verify_sources --all           # active=False 소스도 검사
"""

import argparse
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import feedparser
import httpx

from app.db.models import SourceType
from app.db.seed_sources import ALL_SOURCES, SourceSeed

USER_AGENT = "ai-career-brief/0.1 (personal, non-commercial; daily digest)"
REQUEST_INTERVAL_SEC = 2.0  # 사이트에 부담을 주지 않도록 요청 간 간격
REPORT_PATH = Path("docs/sources-verification.md")


def check_robots(client: httpx.Client, url: str) -> str:
    parts = urlsplit(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    try:
        res = client.get(robots_url)
    except httpx.HTTPError as e:
        return f"확인 실패 ({type(e).__name__})"
    if res.status_code == 404:
        return "robots.txt 없음 (허용)"
    if res.status_code >= 400:
        return f"robots.txt {res.status_code}"
    parser = RobotFileParser()
    parser.parse(res.text.splitlines())
    return "허용" if parser.can_fetch(USER_AGENT, url) else "**금지**"


def check_content(source: SourceSeed, res: httpx.Response) -> str:
    if source.type == SourceType.RSS:
        feed = feedparser.parse(res.content)
        if not feed.entries:
            return "RSS 아님 / 항목 없음"
        dates = [e.get("published") or e.get("updated") for e in feed.entries]
        latest = next((d for d in dates if d), "날짜 없음")
        return f"RSS {len(feed.entries)}개, 최신: {latest}"
    if source.type == SourceType.API:
        try:
            data = res.json()
        except ValueError:
            return "JSON 아님"
        return f"JSON {type(data).__name__} ({len(data)}개)"
    size_kb = len(res.content) / 1024
    hint = " — 내용이 적음, JS 렌더링 필요 가능성" if size_kb < 10 else ""
    return f"HTML {size_kb:.0f}KB{hint}"


def verify(source: SourceSeed, client: httpx.Client) -> dict[str, str]:
    row = {"name": source.name, "url": source.url, "robots": "-", "http": "-", "content": "-"}
    if not source.url:
        row["content"] = "URL 없음"
        return row
    row["robots"] = check_robots(client, source.url)
    time.sleep(REQUEST_INTERVAL_SEC)
    try:
        res = client.get(source.url)
    except httpx.HTTPError as e:
        row["http"] = f"실패 ({type(e).__name__})"
        return row
    row["http"] = str(res.status_code)
    if str(res.url) != source.url:
        row["http"] += f" → {res.url}"
    if res.is_success:
        row["content"] = check_content(source, res)
    return row


def to_markdown(rows: list[dict[str, str]]) -> str:
    lines = [
        f"# 소스 검증 결과 ({datetime.now(UTC):%Y-%m-%d %H:%M} UTC)",
        "",
        "`python -m scripts.verify_sources --write`로 생성됨. 조사 근거는 docs/sources.md 참고.",
        "",
        "| 소스 | URL | robots.txt | HTTP | 내용 |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['name']} | {r['url']} | {r['robots']} | {r['http']} | {r['content']} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help=f"{REPORT_PATH}에 저장")
    parser.add_argument("--all", action="store_true", help="active=False 소스도 검사")
    args = parser.parse_args()

    targets = [s for s in ALL_SOURCES if s.active or args.all]
    with httpx.Client(
        headers={"User-Agent": USER_AGENT}, timeout=15, follow_redirects=True
    ) as client:
        rows = []
        for source in targets:
            print(f"checking {source.name} ...", flush=True)
            rows.append(verify(source, client))

    report = to_markdown(rows)
    print()
    print(report)
    if args.write:
        REPORT_PATH.write_text(report, encoding="utf-8")
        print(f"saved to {REPORT_PATH}")


if __name__ == "__main__":
    main()
