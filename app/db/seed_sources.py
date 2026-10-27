"""수집 소스 초기 데이터 (SPEC 섹션 7).

원칙
- URL은 추측하지 않는다. 공식 사이트·공식 공지·언론 보도 등 근거가 있는 것만 넣는다.
  근거는 config["evidence"], 조사 날짜는 config["checked_on"] (자세한 내용: docs/sources.md).
- RSS가 없는 사이트는 type=HTML + config["link_pattern"] (collectors/html_list.py).
- URL·패턴을 확인하지 못한 소스는 active=False + config["inactive_reason"].
- access(무료/유료)·language는 SPEC_ADDENDUM_01. 현재 seed에는 유료 소스가 없다
  (기업 공식 블로그·공공기관·채용 포털·공공데이터 API).
- "실제로 받아지는지 / robots.txt가 허용하는지"는 scripts/verify_sources.py로 따로 확인한다.

실행 (이름 기준 upsert — 여러 번 실행해도 중복 생기지 않음):
    python -m app.db.seed_sources
"""

from dataclasses import dataclass, field

from sqlalchemy import select

from app.db.models import Source, SourceAccess, SourceLanguage, SourceType
from app.db.session import SessionLocal

CHECKED_ON = "2026-10-27"


@dataclass
class SourceSeed:
    name: str
    type: SourceType
    url: str
    tier: int  # 1 = 1차 출처(기업·기관 공식), 2 = 연구기관 분석·집계
    active: bool
    # SPEC_ADDENDUM_01. None = 확인 못 함 (추측해서 채우지 않는다)
    access: SourceAccess | None
    language: SourceLanguage | None
    config: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# AI 동향 (type=rss/api)
# ---------------------------------------------------------------------------
AI_SOURCES = [
    SourceSeed(
        name="Anthropic News",
        type=SourceType.HTML,
        url="https://www.anthropic.com/news",
        tier=1,
        active=True,
        access=SourceAccess.FREE,
        language=SourceLanguage.EN,
        config={
            # 기사: /news/<slug>, 카테고리(/news/product 등)는 제목 길이로 걸러짐
            "link_pattern": r"^/news/[^/]+$",
            "note": (
                "공식 RSS 없음 → 목록 페이지 HTML 수집. 2026-10-27 직접 접속해 18개 기사 추출 확인"
            ),
            "evidence": [
                "https://feeder.co/discover/df052969a2/anthropic-com-news",
            ],
        },
    ),
    SourceSeed(
        name="OpenAI News",
        type=SourceType.RSS,
        url="https://openai.com/news/rss.xml",
        tier=1,
        active=True,
        access=SourceAccess.FREE,
        language=SourceLanguage.EN,
        config={
            "note": "피드 항목이 날짜순이 아닐 수 있음 → 수집 시 published로 정렬",
            "evidence": [
                "https://feeder.co/knowledge-base/rss-content/ai-news-rss-feeds/",
                "https://community.openai.com/t/openai-website-rss-feed-inquiry/733747",
            ],
        },
    ),
    SourceSeed(
        name="Google DeepMind Blog",
        type=SourceType.RSS,
        url="https://deepmind.google/blog/rss.xml",
        tier=1,
        active=True,
        access=SourceAccess.FREE,
        language=SourceLanguage.EN,
        config={
            "evidence": [
                "https://feeder.co/knowledge-base/rss-content/ai-news-rss-feeds/",
            ],
        },
    ),
    SourceSeed(
        name="Meta AI Blog",
        type=SourceType.HTML,
        url="https://ai.meta.com/blog/",
        tier=1,
        active=False,
        access=SourceAccess.FREE,
        language=SourceLanguage.EN,
        config={
            "inactive_reason": (
                "link_pattern 미확인: 이 환경에서 사이트 접속이 막혀 있음. "
                "python -m scripts.verify_sources --all 의 경로 통계를 보고 설정"
            ),
            "note": "공식 RSS 없음. JS 렌더링 페이지일 가능성 → 링크 0개면 Playwright(M5)",
            "evidence": [
                "https://feeder.co/knowledge-base/rss-content/ai-news-rss-feeds/",
            ],
        },
    ),
    SourceSeed(
        name="NVIDIA Blog",
        type=SourceType.RSS,
        url="https://blogs.nvidia.com/feed/",
        tier=1,
        active=True,
        access=SourceAccess.FREE,
        language=SourceLanguage.EN,
        config={
            "note": "NVIDIA RSS 이용 조건: 개인·비상업적 정보 목적만 허용",
            "evidence": [
                "https://www.nvidia.com/llms.txt",
                "https://www.nvidia.com/en-eu/about-nvidia/rss",
            ],
        },
    ),
    SourceSeed(
        name="Hugging Face Daily Papers",
        type=SourceType.API,
        url="https://huggingface.co/api/daily_papers",
        tier=2,
        active=True,
        access=SourceAccess.FREE,
        language=SourceLanguage.EN,
        config={
            "evidence": [
                "SPEC.md 섹션 7 (사용자 지정)",
            ],
        },
    ),
    SourceSeed(
        name="Epoch AI",
        type=SourceType.HTML,
        url="https://epoch.ai/latest",
        tier=2,
        active=False,
        access=SourceAccess.FREE,
        language=SourceLanguage.EN,
        config={
            "inactive_reason": (
                "link_pattern 미확인: 이 환경에서 사이트 접속이 막혀 있음. "
                "python -m scripts.verify_sources --all 의 경로 통계를 보고 설정"
            ),
            "note": "공식 RSS 못 찾음. /latest가 연구·데이터·뉴스레터 통합 목록",
            "evidence": [
                "https://epochai.substack.com/about",
            ],
        },
    ),
    SourceSeed(
        name="Stanford HAI News",
        type=SourceType.HTML,
        url="https://hai.stanford.edu/news",
        tier=2,
        active=True,
        access=SourceAccess.FREE,
        language=SourceLanguage.EN,
        config={
            # 검색 결과의 기사 URL이 모두 hai.stanford.edu/news/<slug> 형태
            "link_pattern": r"^/news/[^/]+$",
            "note": "RSS 못 찾음 → 목록 페이지 HTML 수집. 페이지 접속은 아직 미검증",
            "evidence": [
                "https://hai.stanford.edu/news/ai-doesnt-have-to-mean-layoffs",
            ],
        },
    ),
    SourceSeed(
        name="소프트웨어정책연구소(SPRi)",
        type=SourceType.HTML,
        url="https://spri.kr",
        tier=2,
        active=False,
        access=SourceAccess.FREE,
        language=SourceLanguage.KO,
        config={
            "inactive_reason": (
                "보고서 목록 페이지 URL과 link_pattern 미확인 (사이트 접속이 막혀 있음)"
            ),
        },
    ),
    SourceSeed(
        name="과학기술정보통신부 보도자료",
        type=SourceType.HTML,
        url="https://www.msit.go.kr",
        tier=1,
        active=False,
        access=SourceAccess.FREE,
        language=SourceLanguage.KO,
        config={
            "inactive_reason": (
                "보도자료 목록 페이지 URL과 link_pattern 미확인 (사이트 접속이 막혀 있음)"
            ),
            "note": "개별 보도자료는 msit.go.kr/bbs/view.do 형태 (국회도서관 목록에서 확인)",
        },
    ),
]

# ---------------------------------------------------------------------------
# 그룹 채용 포털 (type=career_portal) — 수집은 1일 1회, robots.txt 준수
# GS는 그룹 통합 채용 사이트가 없어 제외 (2026-10-27 사용자 결정)
# ---------------------------------------------------------------------------
PORTAL_SOURCES = [
    SourceSeed(
        name="삼성",
        type=SourceType.CAREER_PORTAL,
        url="https://www.samsungcareers.com",
        tier=1,
        active=True,
        access=SourceAccess.FREE,
        language=SourceLanguage.KO,
        config={
            "note": "지원은 회원가입 필요. 공고 목록이 비로그인으로 보이는지 확인 필요",
            "evidence": [
                "https://news.samsung.com/kr/%ec%82%bc%ec%84%b1-2023%eb%85%84-%ed%95%98%eb%b0%98%ea%b8%b0-%ea%b3%b5%ec%b1%84-%ec%8b%a4%ec%8b%9c",
            ],
        },
    ),
    SourceSeed(
        name="SK",
        type=SourceType.CAREER_PORTAL,
        url="https://www.skcareers.com",
        tier=1,
        active=True,
        access=SourceAccess.FREE,
        language=SourceLanguage.KO,
        config={
            "note": "근거가 2020년 기사 → 현재 운영 여부 확인 필요",
            "evidence": [
                "https://kbmaeil.com/article/202009060287254",
            ],
        },
    ),
    SourceSeed(
        name="현대자동차",
        type=SourceType.CAREER_PORTAL,
        url="https://talent.hyundai.com",
        tier=1,
        active=True,
        access=SourceAccess.FREE,
        language=SourceLanguage.KO,
        config={
            "note": "현대차 단독 포털 (기아 등 일부 계열사는 별도 사이트)",
            "evidence": [
                "https://www.wikitree.co.kr/articles/1125154",
            ],
        },
    ),
    SourceSeed(
        name="LG",
        type=SourceType.CAREER_PORTAL,
        url="https://careers.lg.com",
        tier=1,
        active=True,
        access=SourceAccess.FREE,
        language=SourceLanguage.KO,
        config={
            "note": "LG전자(lge-recruit.com), LG디스플레이(lgd-recruit.com)는 자체 사이트도 사용",
            "evidence": [
                "https://cse.snu.ac.kr/en/community/notice/24980",
            ],
        },
    ),
    SourceSeed(
        name="한화",
        type=SourceType.CAREER_PORTAL,
        url="https://www.hanwhain.com",
        tier=1,
        active=True,
        access=SourceAccess.FREE,
        language=SourceLanguage.KO,
        config={
            "evidence": [
                "https://newstomato.com/ReadNews.aspx?no=541744",
            ],
        },
    ),
    SourceSeed(
        name="롯데",
        type=SourceType.CAREER_PORTAL,
        url="https://recruit.lotte.co.kr",
        tier=1,
        active=True,
        access=SourceAccess.FREE,
        language=SourceLanguage.KO,
        config={
            "note": "3·6·9·12월 정기 공고. 캠페인 사이트(lotte-36912recruit.com)도 병행",
            "evidence": [
                "https://cse.snu.ac.kr/en/community/notice/24184",
            ],
        },
    ),
    SourceSeed(
        name="포스코",
        type=SourceType.CAREER_PORTAL,
        url="https://recruit.posco.com",
        tier=1,
        active=True,
        access=SourceAccess.FREE,
        language=SourceLanguage.KO,
        config={
            "note": "2023·2024 공채 접수처. 2026 하반기 접수 URL은 미확인",
            "evidence": [
                "https://newsroom.posco.com/kr/%ED%8F%AC%EC%8A%A4%EC%BD%94%EA%B7%B8%EB%A3%B9-2023%EB%85%84-%ED%95%98%EB%B0%98%EA%B8%B0-%EC%8B%A0%EC%9E%85%EC%82%AC%EC%9B%90-%EA%B3%B5%EC%B1%84-%EC%8B%9C%EC%9E%91",
            ],
        },
    ),
    SourceSeed(
        name="HD현대",
        type=SourceType.CAREER_PORTAL,
        url="https://recruit.hd.com",
        tier=1,
        active=True,
        access=SourceAccess.FREE,
        language=SourceLanguage.KO,
        config={
            "note": (
                "2024 하반기 접수처. 2026 하반기 공채는 hd-recruit2026.com(캠페인 사이트)로 접수"
            ),
            "evidence": [
                "https://cse.snu.ac.kr/en/community/notice/23438",
            ],
        },
    ),
    SourceSeed(
        name="KT",
        type=SourceType.CAREER_PORTAL,
        url="https://recruit.kt.com/careers",
        tier=1,
        active=True,
        access=SourceAccess.FREE,
        language=SourceLanguage.KO,
        config={
            "evidence": [
                "https://biz.korea.ac.kr/cdc/recruitment/recruitment_view?no=14469",
            ],
        },
    ),
]

# ---------------------------------------------------------------------------
# 공식 API
# ---------------------------------------------------------------------------
API_SOURCES = [
    SourceSeed(
        name="고용24 공채속보",
        type=SourceType.API,
        url="https://www.data.go.kr/data/15031951/openapi.do",
        tier=1,
        active=False,
        access=SourceAccess.FREE,
        language=SourceLanguage.KO,
        config={
            "inactive_reason": (
                "엔드포인트·파라미터 미확인 + 인증키(WORK24_API_KEY) 필요. url은 API 문서 페이지"
            ),
            "note": (
                "고용24 자체 OPEN-API는 기업회원 전용이라는 안내가 있음 "
                "→ 공공데이터포털 쪽으로 신청"
            ),
            "evidence": [
                "https://www.data.go.kr/data/15031951/openapi.do",
                "https://m.work24.go.kr/cm/e/a/0110/selectOpenApiIntro.do",
            ],
        },
    ),
]

ALL_SOURCES = AI_SOURCES + PORTAL_SOURCES + API_SOURCES

# 목록에서 뺀 소스. seed 실행 시 DB에 남아 있으면 지운다 (아직 수집 데이터가 없을 때만 안전).
REMOVED_SOURCE_NAMES = ["GS"]


def seed() -> None:
    with SessionLocal() as session:
        for s in ALL_SOURCES:
            config = {**s.config, "checked_on": CHECKED_ON}
            row = session.scalar(select(Source).where(Source.name == s.name))
            if row is None:
                row = Source(name=s.name)
                session.add(row)
            row.type, row.url, row.tier, row.active, row.config = (
                s.type,
                s.url,
                s.tier,
                s.active,
                config,
            )
            row.access, row.language = s.access, s.language
            # subscribed, price_note는 사용자 상태라 seed가 덮어쓰지 않는다.
        for name in REMOVED_SOURCE_NAMES:
            removed = session.scalar(select(Source).where(Source.name == name))
            if removed is not None:
                session.delete(removed)
        session.commit()
    active = sum(s.active for s in ALL_SOURCES)
    print(f"seeded {len(ALL_SOURCES)} sources ({active} active)")


if __name__ == "__main__":
    seed()
