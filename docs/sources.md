# 수집 소스 조사 (2026-10-27)

## ✅ 실제 접속 검증 결과 (2026-10-28, 네트워크 허용 후)

전체 표: [sources-verification.md](sources-verification.md). 20곳 중 **17곳 active**.

- **AI 동향 10곳 모두 수집 가능.** 검색으로 못 찾았던 공식 피드를 직접 접속해서 찾았다:
  - Epoch AI: `epoch.ai/atom.xml` (HTML `<link rel=alternate>`에 있었음) → RSS로 전환
  - 과기정통부: `msit.go.kr/user/rss/rss.do?bbsSeqNo=94` ("RSS 이용안내" 페이지) → RSS로 전환
  - Meta AI(`^/blog/[^/]+/?$`, 정적 HTML에서 5개), SPRi(보고서 목록 `/posts?code=data_all`, 12개) → HTML 수집 패턴 확정
- **채용 포털**: 삼성·SK는 정적 HTML이 있음. 현대차(접속 대기열 페이지), LG·한화·HD현대·KT(HTML 2~3KB)는 JS 렌더링 필요 → M5에서 Playwright.
- **비활성 2곳**:
  - 롯데: robots.txt가 403 → 허용 여부를 확인할 수 없음. 다른 User-Agent로 다시 시도하는 등의 우회는 하지 않았다. → **제외 (사용자 결정)**, 공고 Inbox로 입력.
  - 포스코: 예전 주소 `recruit.posco.com`은 DNS에서 조회되지 않는다. 2026 하반기 공고의 bit.ly 링크가 `www.poscorecruit.com`으로 301 리다이렉트된다 → seed URL을 교체했다. robots.txt는 허용 도메인 추가 후 확인.
- **고용24 공채속보 API**: 무료, 활용신청 시 **자동승인**, 이용허락범위는 출처표시·비상업·변경금지(공공누리 4유형). 요청 주소는 활용신청 후 상세 화면에서 확인해야 한다.

---


SPEC 섹션 7의 초기 소스에 대한 조사 결과 (GS는 그룹 통합 채용 사이트가 없어 사용자 결정으로 제외 → 20개). seed 데이터는 `app/db/seed_sources.py`.

- **조사 방법**: 웹 검색으로 공식 URL과 그 근거(공식 뉴스룸, 공식 문서, 대학 취업센터에 게시된 공고문, 언론 보도)를 찾았다.
- **아직 안 한 것**: 사이트에 직접 접속하는 검증(HTTP 응답, robots.txt, RSS 파싱). 조사한 클라우드 환경의 네트워크 정책이 해당 도메인을 막고 있었다.
  → 네트워크가 열린 곳(로컬 PC 또는 EC2)에서 `python -m scripts.verify_sources --all --write` 실행 → `docs/sources-verification.md` 생성.

근거 수준: **A** = 공식 출처(해당 기관 사이트·뉴스룸), **B** = 공고문 인용(대학 취업센터·언론), **C** = 제3자 집계 사이트.

## AI 동향 (10곳) — RSS 3곳 + API 1곳 + HTML 수집 6곳

RSS가 없는 곳은 목록 페이지 HTML에서 기사 링크를 뽑는다 (`type=html`, `app/agents/background/collectors/html_list.py`).
사이트별 차이는 `config["link_pattern"]`(기사 URL 경로 정규식) 하나뿐이다.

| HTML 소스 | 상태 |
|---|---|
| Anthropic | ✅ **실제 수집 확인** (2026-10-27, robots.txt 허용, 기사 18개, 패턴 `^/news/[^/]+$`) |
| Stanford HAI | 패턴 `^/news/[^/]+$` 설정 (검색된 기사 URL 형태 기준), 접속은 미검증 → active |
| Meta AI, Epoch AI | 패턴 미확인 → inactive. verify 스크립트가 출력하는 경로 통계로 패턴 결정 |
| SPRi, 과기정통부 | 목록 페이지 URL부터 미확인 → inactive |


| 소스 | URL | RSS | 근거 | seed 상태 |
|---|---|---|---|---|
| Anthropic | anthropic.com/news | ❌ 공식 RSS 없음 (직접 접속해서 확인함) | C [feeder](https://feeder.co/discover/df052969a2/anthropic-com-news) | inactive |
| OpenAI | openai.com/news/rss.xml | ✅ | C [feeder](https://feeder.co/knowledge-base/rss-content/ai-news-rss-feeds/), [OpenAI 커뮤니티](https://community.openai.com/t/openai-website-rss-feed-inquiry/733747) | active |
| Google DeepMind | deepmind.google/blog/rss.xml | ✅ | C [feeder](https://feeder.co/knowledge-base/rss-content/ai-news-rss-feeds/) | active |
| Meta AI | ai.meta.com/blog | ❌ 공식 RSS 없음 | C [feeder](https://feeder.co/knowledge-base/rss-content/ai-news-rss-feeds/) | inactive |
| NVIDIA | blogs.nvidia.com/feed/ | ✅ (개인·비상업 용도만 허용) | A [nvidia.com/llms.txt](https://www.nvidia.com/llms.txt), [RSS 안내](https://www.nvidia.com/en-eu/about-nvidia/rss) | active |
| Hugging Face Daily Papers | huggingface.co/api/daily_papers | API (JSON) | SPEC 지정 | active |
| Epoch AI | epoch.ai/latest | ❓ 공식 피드 못 찾음 | [Substack](https://epochai.substack.com/about)에 뉴스레터 있음 | inactive |
| Stanford HAI | hai.stanford.edu/news | ❓ 못 찾음 (이메일 구독만 있음) | — | inactive |
| SPRi | spri.kr | ❓ 못 찾음 | — | inactive |
| 과기정통부 | msit.go.kr | ❓ 공식 RSS 못 찾음 (뉴스와이어 제3자 RSS만 있음) | — | inactive |

## 그룹 채용 포털 (9곳, GS 제외)

| 그룹 | URL | 근거 | 메모 |
|---|---|---|---|
| 삼성 | samsungcareers.com | A [삼성 뉴스룸](https://news.samsung.com/kr/%ec%82%bc%ec%84%b1-2023%eb%85%84-%ed%95%98%eb%b0%98%ea%b8%b0-%ea%b3%b5%ec%b1%84-%ec%8b%a4%ec%8b%9c) | 지원하려면 회원가입. 공고 목록이 로그인 없이 보이는지 확인 필요 |
| SK | skcareers.com | B [경북매일 2020](https://kbmaeil.com/article/202009060287254) | 근거가 오래됨 → 현재 운영 여부 확인 필요 |
| 현대차 | talent.hyundai.com | B [위키트리 2026.3](https://www.wikitree.co.kr/articles/1125154) | 기아 등 일부 계열사는 별도 사이트 |
| LG | careers.lg.com | B [서울대 공지 2026](https://cse.snu.ac.kr/en/community/notice/24980) | LG전자·LG디스플레이는 자체 채용 사이트도 사용 |
| 한화 | hanwhain.com | B [뉴스토마토](https://newstomato.com/ReadNews.aspx?no=541744) | 2026 상반기 공고에서도 사용 |
| 롯데 | recruit.lotte.co.kr | B [서울대 공지 2026.9](https://cse.snu.ac.kr/en/community/notice/24184) | 3·6·9·12월 정기 공고 |
| 포스코 | recruit.posco.com | A [포스코 뉴스룸 2023](https://newsroom.posco.com/kr/%ED%8F%AC%EC%8A%A4%EC%BD%94%EA%B7%B8%EB%A3%B9-2023%EB%85%84-%ED%95%98%EB%B0%98%EA%B8%B0-%EC%8B%A0%EC%9E%85%EC%82%AC%EC%9B%90-%EA%B3%B5%EC%B1%84-%EC%8B%9C%EC%9E%91) | 2026 하반기 접수 URL은 미확인 |
| HD현대 | recruit.hd.com | B [서울대 공지 2024](https://cse.snu.ac.kr/en/community/notice/23438) | ⚠️ 2026 하반기 공채는 캠페인 사이트(hd-recruit2026.com)로 접수 |
| KT | recruit.kt.com/careers | B [고려대 공지 2026](https://biz.korea.ac.kr/cdc/recruitment/recruitment_view?no=14469) | 그룹사 공고 포함 |

## 공식 API

| API | 상태 |
|---|---|
| 고용24 공채속보 | 공공데이터포털에 [한국고용정보원_워크넷 공채속보 공채기업목록 및 상세정보](https://www.data.go.kr/data/15031951/openapi.do)가 있음. **엔드포인트·파라미터는 아직 미확인.** ⚠️ 고용24 자체 OPEN-API는 [기업회원 전용](https://m.work24.go.kr/cm/e/a/0110/selectOpenApiIntro.do)이라는 안내가 있어서 공공데이터포털 쪽으로 키를 신청해야 할 가능성이 큼 |

## 남은 결정 / TODO

1. ~~RSS 없는 6곳~~ → HTML 수집으로 결정. Meta AI·Epoch·SPRi·과기정통부는 네트워크가 열린 곳에서 패턴 확인 필요.
2. ~~GS~~ → 제외로 결정.
3. **HD현대·롯데처럼 공채마다 캠페인 사이트를 따로 여는 곳**: 상시 포털만 수집하고, 캠페인 사이트는 사용자가 공고 Inbox로 직접 입력(M3).
4. **포털 공고 목록이 로그인 없이 보이는지 + JS 렌더링이 필요한지**: verify 스크립트 결과로 판단. M5에서 Playwright로 확인.
5. **공채속보 API**: 공공데이터포털에서 키 신청 → 엔드포인트 확인.

## 유료/무료·언어 (SPEC_ADDENDUM_01, 2026-10-28 반영)

현재 seed 20곳은 모두 `access=free`다. 유료 소스는 아직 없다.
- 영어(en) 8곳: Anthropic, OpenAI, Google DeepMind, Meta AI, NVIDIA, Hugging Face, Epoch AI, Stanford HAI
- 한국어(ko) 12곳: SPRi, 과기정통부, 채용 포털 9곳, 고용24 공채속보
- 근거 수준: 기업 공식 블로그·공공기관·채용 포털·공공데이터 API라는 소스 성격으로 판단했다. Epoch AI는 [제3자 디렉터리](https://www.toolmage.com/de/tool/epoch-ai/)에서 "보고서·뉴스레터 전부 무료"로 확인. 각 소스의 본문을 열어 페이월을 직접 확인한 것은 아니다 → verify 실행 때 함께 확인.
- 권위 기준으로 유료 후보(예: 해외 AI 전문 매체, 국내 경제지)를 추가할지는 별도 결정.
