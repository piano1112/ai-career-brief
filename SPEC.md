# SPEC — AI 커리어 브리핑 앱 (개인용)

> 이 문서는 Claude Code가 구현할 때 기준이 되는 명세다. 기획 배경은 별도 기획 문서에 있다.
> 작성일: 2026-10-28 · 사용자: 1명 (개발자 본인)

---

## 0. 한 줄 요약

매일 07:00에 "지금 나에게 중요한" AI 동향 + 대기업 채용 정보 + 오늘 할 일 제안을 비주얼 리포트로 발행하고,
동시에 대화를 통해 사용자를 계속 더 정확히 알아가는 개인용 웹앱.

---

## 1. 이번 프로토타입 범위 (Milestone 1–2)

**먼저 이것만 만든다.** 나머지 섹션은 설계가 어긋나지 않도록 전체 맥락으로 제공한다.

### Milestone 1 — 뼈대 (목표: 11/2)
- [ ] repo 구조, Docker Compose (`web`, `worker`, `db`) 로컬 실행
- [ ] FastAPI + Jinja + HTMX + Tailwind 기본 레이아웃 (사이드바: 브리핑 / 대화 / 지원현황 / 캘린더 / 나에 대해)
- [ ] PostgreSQL 스키마 (섹션 4 전체) + Alembic 마이그레이션
- [ ] `worker` 컨테이너에서 APScheduler가 돌아가는 것 확인 (더미 job 1개)
- [ ] `.env.example`, README에 실행 방법

### Milestone 2 — 대화 에이전트 + User Model (목표: 11/9)
- [ ] 채팅 화면 (HTMX, 스트리밍 응답)
- [ ] Claude API tool use 기반 대화 에이전트 루프 (섹션 5.2)
- [ ] 도구: `save_user_fact`, `update_user_fact`, `list_user_facts`, `emit_event`
- [ ] "나에 대해" 화면: user_fact를 카테고리별로 보기, 직접 수정/삭제/확인(confirmed) 토글
- [ ] 에이전트가 추측한 사실은 `confirmed=false`로 저장, 사용자 확인 시 true

**완료 기준**: 채팅으로 "나는 Python이 제일 익숙해"라고 말하면 → user_fact가 생기고 → "나에 대해" 화면에 미확인 상태로 보이고 → 내가 확인/수정할 수 있다.

---

## 2. 기술 스택

| 영역 | 선택 | 비고 |
|---|---|---|
| 언어 | Python 3.12 | |
| 웹 | FastAPI | async |
| 템플릿 | Jinja2 + HTMX + Tailwind (CDN 또는 standalone CLI) | SPA 프레임워크 쓰지 않음. 사용자는 프론트 경험 없음 → 단순하고 읽기 쉬운 템플릿 우선 |
| DB | PostgreSQL 16 | SQLAlchemy 2.0 + Alembic |
| LLM | Anthropic Claude API (`anthropic` SDK) | 모델명은 `CLAUDE_MODEL` 환경변수로. 하드코딩 금지 |
| 스케줄러 | APScheduler (worker 프로세스) | 타임존 `Asia/Seoul` |
| 수집 | `feedparser`(RSS), `httpx`, Playwright(JS 렌더링 페이지) | |
| 배포 | AWS EC2 1대 + Docker Compose | 이후 RDS/SQS/EventBridge로 점진 이전 가능하게 결합도 낮게 |

### 코드 원칙
- 사용자는 Python/Java에 익숙, 프론트 경험 없음. **모든 코드는 사용자가 읽고 설명할 수 있어야 한다.** 과한 추상화, 메타프로그래밍 피하기
- LLM 호출은 `app/llm/` 한 곳을 통해서만 (비용 추적, 모델 교체 쉽게)
- 모든 LLM 호출의 입력 토큰/출력 토큰/비용 추정을 `llm_usage` 로그에 남긴다
- 타입 힌트 필수, `ruff` + `pytest`

---

## 3. 아키텍처

```
┌──────────────────────────┐   이벤트(양방향)   ┌──────────────────────────┐
│ 백그라운드 에이전트 (worker) │ ◀──────────────▶ │ 대화 에이전트 (web)          │
│ - 수집 (몇 시간마다)         │                  │ - 온보딩·질문                │
│ - 새 항목만 분석·점수화      │                  │ - 공고 분석·지원현황·전형로그  │
│ - 다음날 리포트 초안 갱신    │                  │ - 일정 관리·알림 전달          │
│ - 마감 감시                 │                  │ - 대화형 피드백·자소서         │
│ - 07:00 리포트 발행         │                  │                            │
└────────────┬─────────────┘                  └─────────────┬──────────────┘
             └──────────────▶ PostgreSQL (공유) ◀───────────┘
                  user_fact · application · item · agent_event ...
```

### 핵심 규칙
1. 두 에이전트는 **직접 호출하지 않는다.** 공유 DB와 `agent_event` 테이블로만 소통한다.
2. 한쪽이 죽어도 다른 쪽은 동작해야 한다.
3. 수집은 LLM 없이 일반 코드로 한다. **새로 들어온 항목만** LLM이 분석한다 (증분 처리).
4. 07:00 발행은 반드시 성공해야 한다 → 아침에는 조립 + 렌더링만. 무거운 분석은 전날 밤까지 끝낸다. 실패 시 전날 초안이라도 발행.
5. 대화 에이전트는 사용자가 앱을 열었을 때만 동작한다. 백그라운드 → 대화 이벤트는 "메시지함"에 쌓였다가 다음 접속 시 전달. `priority=high`만 즉시 알림(Phase 2).

---

## 4. 데이터 모델

모든 테이블: `id uuid PK`, `created_at timestamptz`, `updated_at timestamptz` 기본 포함 (아래에서 생략).

### user_fact — User Model (가장 중요)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| category | enum | `goal`, `experience`, `skill`, `preference`, `weakness_learning`, `lifestyle` |
| content | text | 사실 하나. 짧고 구체적으로 |
| source | text | 어디서 알게 됐는지 (예: "2026-10-28 대화", "이력서 업로드") |
| confirmed | bool | 사용자가 확인했는지. 에이전트 추측은 false |
| superseded_by | uuid FK nullable | 정정된 경우 새 fact를 가리킴. 삭제 대신 이력 보존 |

> 원칙: 경험(experience)은 **본인이 실제로 한 것만** 기록. 팀 프로젝트는 본인 기여를 분리해서 저장. 자소서는 confirmed=true인 experience만 근거로 쓴다.

### message — 대화 기록
| role (`user`/`assistant`/`tool`) | content (text/json) | thread (text, 예: `main`, `feedback:<entry_id>`) |

### job_posting — 수집된 공고
| company_group | company | title | url | deadline (date null) | raw (text) | first_seen | source_id FK |

### application — 지원(예정) 건
| 컬럼 | 설명 |
|---|---|
| posting_id FK nullable | 수집 공고에서 온 경우 |
| company, position | |
| status | enum: `considering`, `applied`, `document_passed`, `test`, `interview`, `offer`, `rejected`, `withdrawn` |
| deadline | date null |
| raw_input | 사용자가 붙여넣은 원문 / 스크린샷 경로 |
| analysis | json: 직무, 스택, 자격요건, 전형절차, 매칭도, 지원 추천 여부 + 근거 |

### application_log — 전형 로그
| application_id FK | stage (text) | kind enum(`event`, `retro`) | content (text) | occurred_at |

> 결과의 "이유"는 알 수 없으므로 저장하지 않는다. 전형 중 있었던 사건과 사용자의 회고만 기록.

### document — 이력서/자소서
| application_id FK null | type enum(`resume`, `cover_letter`, `essay_answer`) | version int | content text |

### calendar_event
| application_id FK null | title | start_at timestamptz | end_at null | kind enum(`deadline`, `test`, `interview`, `manual`) |

### source — 수집 소스
| name | type enum(`rss`, `api`, `career_portal`) | url | tier int (1=최상위) | active bool | config json |

### item — 수집된 동향 항목
| source_id FK | title | url (unique) | published_at | raw (text) | summary | score float null | analyzed_at null |

### briefing / briefing_entry
- briefing: `for_date date unique`, `content json`, `html text`, `status enum(draft, published)`, `published_at`
- briefing_entry: `briefing_id FK`, `section enum(schedule, ai_trend, jobs, suggestion, question)`, `item_id FK null`, `posting_id FK null`, `payload json`

### feedback
| entry_id FK | conversation_summary | outcome (text: 이 피드백으로 무엇이 바뀌었는지) |

### agent_event — 양방향 이벤트 큐
| 컬럼 | 설명 |
|---|---|
| from_agent / to_agent | `background` / `chat` |
| type | 예: `application_updated`, `interest_changed`, `new_posting`, `deadline_soon`, `question_for_user` |
| priority | `low` / `normal` / `high` |
| payload | json |
| status | `pending` / `processed` |
| processed_at | |

### llm_usage
| purpose | model | input_tokens | output_tokens | est_cost_usd | created_at |

---

## 5. 에이전트 상세

### 5.1 공통
- Claude API tool use 사용. 에이전트 = 시스템 프롬프트 + 도구 목록 + 루프
- 시스템 프롬프트에 매번 주입: confirmed user_fact 요약, 오늘 날짜(Asia/Seoul), 진행 중 application 요약
- 언어: 한국어/영어 혼용 사용자. 응답은 사용자 언어를 따른다
- **정확성 원칙**: 모르면 모른다고 한다. 추측은 추측이라고 표시. 사용자에 대한 새 사실은 "이렇게 이해했는데 맞아?"로 확인 후 confirmed 처리

### 5.2 대화 에이전트 (web)
도구 (Milestone 표시):
| 도구 | M | 설명 |
|---|---|---|
| `save_user_fact(category, content, source, confirmed)` | 2 | |
| `update_user_fact(id, content, confirmed)` | 2 | 정정 시 superseded_by로 이력 보존 |
| `list_user_facts(category?)` | 2 | |
| `emit_event(type, priority, payload)` | 2 | to_agent=background |
| `analyze_posting(text_or_image)` | 3 | 공고 분석 → application 생성 (status=considering) |
| `update_application(id, status, ...)` | 3 | 상태 변경 시 calendar_event 자동 생성/수정 |
| `add_application_log(application_id, stage, kind, content)` | 4 | |
| `add_calendar_event(...)` | 4 | |
| `draft_document(application_id, type)` | Phase 2 | |

- 접속 시: `agent_event`에서 `to_agent=chat, status=pending`을 읽어 대화 시작 메시지로 전달 후 processed
- 온보딩 (M3): user_fact가 거의 없으면 온보딩 모드. 카테고리별로 질문, 이력서/GitHub 텍스트 입력 받기

### 5.3 백그라운드 에이전트 (worker)
| job | 주기 | 내용 |
|---|---|---|
| `collect_rss` | 3시간 | source(type=rss) 수집 → item upsert (url unique) |
| `collect_portals` | 1일 1회 (새벽) | Playwright로 그룹 채용 포털 렌더링 → LLM으로 공고 추출 → job_posting upsert, 새 공고만 표시 |
| `collect_public_api` | 1일 1회 | 고용24 공채속보 API |
| `analyze_new` | 수집 후 | analyzed_at null인 item/posting만 user_fact 기준으로 점수화·요약 |
| `process_events` | 10분 | to_agent=background 이벤트 처리 (수집 우선순위, 다음 브리핑 메모 반영) |
| `watch_deadlines` | 1일 2회 | D-3, D-1 마감 → to_agent=chat 이벤트 (D-1은 high) |
| `update_draft` | 분석 후 | 다음날 briefing(draft) 갱신 |
| `publish_briefing` | 매일 07:00 | draft 조립 → HTML 렌더 → published |

---

## 6. 아침 브리핑 구성 (10분 분량)

1. **오늘 맥락** — 오늘/이번 주 일정, 임박한 마감·전형
2. **AI 동향** 3개 내외 — 각 항목: 한 줄 요약 + "왜 나한테 중요한지" + 출처 등급(tier)
3. **채용** — 새 공고(매칭도 순), 마감 임박, 진행 중 전형
4. **오늘의 제안** 1–3개 — 공부/지원/프로젝트 액션 + **근거 필수**
5. **질문 1개** — 나를 더 알기 위한 질문

- 시각적 우선 (사용자는 텍스트 많은 화면을 싫어함): 카드 레이아웃, 아이콘/배지, 짧은 문장
- 각 항목에 "이야기하기" 버튼 → `thread=feedback:<entry_id>`로 대화 열림

---

## 7. 데이터 소스 (초기 seed)

### 채용 포털 (type=career_portal) — 그룹 10곳
삼성, SK, 현대차, LG, 한화, 롯데, 포스코, HD현대, GS, KT
- URL은 구현 시 각 그룹 공식 채용 사이트를 확인해서 seed에 넣는다 (추측 URL 금지)
- 각 사이트 robots.txt 확인, 요청 간격 충분히, User-Agent 명시, 1일 1회
- 접근 불가(로그인 필수 등)한 곳은 `active=false` + 사유를 config에 기록

### 공식 API
- 고용24(워크넷) 공채속보 API — 공공데이터포털 인증키 필요 (`WORK24_API_KEY`)
- 공공기관 채용정보 조회서비스 — Phase 2

### AI 동향 (type=rss/api) — 10곳
Anthropic, OpenAI, Google DeepMind, Meta AI, NVIDIA 블로그, Hugging Face Daily Papers (`GET https://huggingface.co/api/daily_papers`), Epoch AI, Stanford HAI, 소프트웨어정책연구소(SPRi), 과기정통부 AI 보도자료
- RSS 제공 여부를 하나씩 확인. RSS 없는 곳은 일단 `active=false`로 두고 보고

### 하지 않는 것
- 잡코리아·캐치·사람인 등 채용 플랫폼 자동 수집 금지 (사용자가 공고 Inbox로 직접 입력)

---

## 8. 디렉터리 구조 (제안)

```
app/
  main.py              # FastAPI 앱
  config.py            # 환경변수
  db/                  # models.py, session.py
  llm/                 # client.py (모든 Claude 호출 단일 진입점), usage.py
  agents/
    chat/              # loop.py, tools.py, prompts.py
    background/        # jobs/*.py, scheduler.py
  events.py            # agent_event 읽기/쓰기 헬퍼
  web/
    routes/            # briefing.py, chat.py, applications.py, calendar.py, me.py
    templates/
    static/
worker.py              # 백그라운드 엔트리포인트
migrations/
tests/
docker-compose.yml
.env.example
```

---

## 9. 환경변수

```
ANTHROPIC_API_KEY=
CLAUDE_MODEL=
DATABASE_URL=postgresql+psycopg://...
TZ=Asia/Seoul
BRIEFING_PUBLISH_TIME=07:00
WORK24_API_KEY=
```

인증: 1인용이지만 인터넷에 노출되므로 최소한의 로그인(단일 계정, 비밀번호 해시 + 세션 쿠키)은 Milestone 1에 포함.

---

## 10. Non-goals (v1)
- 다중 사용자, 회원가입
- 자동 지원, 외부 캘린더 연동
- AI·채용 외 분야, 해외 채용
- SPA 프레임워크(React 등)

---

## 11. 전체 일정 (참고)

| 기간 | 작업 |
|---|---|
| 10/28–11/2 | M1 뼈대 + 소스 검증 |
| 11/3–11/9 | M2 대화 에이전트 + User Model |
| 11/10–11/16 | M3 온보딩 + 공고 Inbox |
| 11/17–11/23 | M4 지원현황 + 전형 로그 + 캘린더 |
| 11/24–11/30 | M5 수집 + 아침 브리핑 |
| 12/1 | 매일 사용 시작 |
| 12/1–12/7 | 대화형 피드백 |
| 12/8–12/14 | 이력서·자소서 |
| 12/15–12/21 | 동향 분석, 포털 확대 |
| 12/22–12/25 | 다듬기, README → 완성 |

---

## 12. Claude Code에게

- 시작 전에 이 SPEC을 읽고, **Milestone 1부터** 진행한다. 범위 밖 기능을 미리 만들지 않는다.
- 각 Milestone 끝에: 무엇을 만들었는지, 어떻게 실행/확인하는지, 남은 이슈를 짧게 보고한다.
- 설계 결정이 SPEC과 다르게 필요하면 먼저 이유와 함께 물어본다.
- 외부 URL, API 엔드포인트, 모델명은 추측하지 말고 확인한다. 확인 못 하면 TODO로 남기고 보고한다.
- 사용자가 코드를 이해하고 면접에서 설명할 수 있도록, 주요 설계 선택에는 짧은 주석이나 `docs/decisions.md`에 기록(결정 / 이유 / 대안)을 남긴다.
