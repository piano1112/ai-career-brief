# 설계 결정 기록

형식: **결정 / 이유 / 대안**. 면접에서 "왜 이렇게 했나요?"에 답할 수 있도록 남긴다.

---

## 001. DB 접근은 동기(sync) SQLAlchemy

- **결정**: FastAPI는 async지만 DB 세션은 동기 `Session`을 쓰고, DB를 쓰는 라우트는 `def`로 만든다.
- **이유**: 1인용이라 동시 요청이 거의 없다. 동기 코드가 읽기·디버깅이 쉽고, worker(APScheduler)와 같은 코드를 공유할 수 있다. FastAPI는 `def` 라우트를 스레드풀에서 돌리므로 이벤트 루프를 막지 않는다.
- **대안**: `AsyncSession` + asyncpg. 동시성이 필요해지면 (예: LLM 스트리밍과 DB를 함께 다루는 부분) 그 부분만 바꾼다.

## 002. 로그인은 세션 쿠키 + `.env`의 bcrypt 해시

- **결정**: 사용자 테이블 없이 `ADMIN_USERNAME` / `ADMIN_PASSWORD_HASH`를 환경변수로 두고, 로그인 상태는 서명된 쿠키(Starlette `SessionMiddleware`)에 저장. 인증 체크는 미들웨어 한 곳에서.
- **이유**: 1인용(SPEC Non-goals: 다중 사용자 없음). 테이블·회원가입이 불필요. 미들웨어로 처리하면 새 라우트를 만들 때 인증을 빠뜨릴 수 없다.
- **대안**: user 테이블 + 서버측 세션 저장소. 다중 사용자가 되면 필요.
- **한계**: 로그인 시도 횟수 제한(brute force 방어) 없음 → 인터넷 노출 전 추가 필요 (아래 남은 이슈).

## 003. htmx / Tailwind를 CDN 대신 파일로 포함 (`static/vendor/`)

- **결정**: npm 공식 패키지(`htmx.org@2.0.11`, `@tailwindcss/browser@4.3.3`)의 배포 파일을 repo에 넣는다. 파일명에 버전을 포함.
- **이유**: 07:00 브리핑 화면이 외부 CDN 장애에 영향받지 않게. 빌드 도구(Node) 없이 Python만으로 실행 가능.
- **대안**: Tailwind standalone CLI로 CSS를 빌드. `@tailwindcss/browser`는 브라우저에서 CSS를 생성하므로 첫 로딩이 약간 느리다. 화면이 많아지면 standalone CLI 빌드로 바꾸는 것을 검토.

## 004. PostgreSQL native enum + 자주 바뀔 구조는 JSONB

- **결정**: 상태·종류 컬럼은 PostgreSQL enum, `analysis`/`payload`/`config` 등은 JSONB.
- **이유**: enum은 잘못된 값을 DB가 막아준다. JSONB는 아직 구조가 확정되지 않은 LLM 분석 결과를 마이그레이션 없이 바꿀 수 있다.
- **대안**: enum 대신 text + CHECK 제약 (값 추가가 더 쉬움). enum에 값을 추가할 때는 `ALTER TYPE ... ADD VALUE` 마이그레이션을 직접 작성해야 한다는 점을 기억할 것.

## 005. `message.content`는 JSONB

- **결정**: SPEC의 "text/json"을 JSONB 하나로 저장 (문자열 또는 Claude content block 리스트).
- **이유**: tool use 대화는 `tool_use` / `tool_result` 블록 리스트라 텍스트로는 저장할 수 없다. 한 컬럼으로 두 경우를 다 담는다.
- **대안**: `content_text` + `content_json` 두 컬럼.

## 006. 마이그레이션은 web 컨테이너 시작 시에만 실행

- **결정**: `web`의 command에서 `alembic upgrade head` 후 uvicorn 시작. worker는 실행하지 않음.
- **이유**: 두 컨테이너가 동시에 마이그레이션하면 충돌할 수 있다.
- **대안**: 별도 `migrate` one-shot 서비스. 배포가 복잡해지면 그쪽으로.

## 007. APScheduler 3.x, `BlockingScheduler`, 메모리 job store

- **결정**: worker는 APScheduler 3.x의 `BlockingScheduler` (timezone `Asia/Seoul`), job은 `scheduler.py` 한 곳에 등록. `coalesce=True`, `max_instances=1`.
- **이유**: 4.x는 아직 pre-release. job 정의가 코드에 있으므로 DB job store가 필요 없다. 밀린 실행은 한 번만 돌린다.
- **대안**: cron + 스크립트, Celery beat (규모 대비 과함), 이후 AWS EventBridge (SPEC 배포 계획).

## 008. 기본 모델 `CLAUDE_MODEL=claude-opus-5-5`

- **결정**: 대화 에이전트 기본 모델은 Claude Opus 5.5.
- **이유**: 현재 Anthropic이 권장하는 기본 모델이고, tool use와 한국어/영어 혼용 대화의 품질을 우선했다. 1인용이라 호출 수가 적어서 비용 차이가 작다. 가격은 입력 $4 / 출력 $20 (100만 토큰당, 2026-10 기준).
- **M2 구현 시 주의할 API 특성**:
  - thinking을 끌 수 없다. 깊이는 `output_config.effort`로만 조절하고, 기본값이 `medium`이니 명시적으로 설정한다.
  - `tool_choice`로 도구 호출을 강제(`any`/`tool`)하면 400 에러가 난다 → `auto` + 프롬프트로 유도한다.
  - 대화 기록은 append-only로 다룬다 (이전 턴을 수정하면 thinking 블록이 무효화됨). `message.content`를 JSONB로 둔 이유와 맞물린다 (005).
- **대안**: Claude Sonnet 5.5 ($2 / $10), Claude Haiku 5.5 ($0.10 / $0.50). 백그라운드 대량 요약·점수화(M5)에는 더 싼 모델이나 Batches API(50% 할인)가 적합할 수 있다. 그때 `llm_usage` 실측값을 보고 `CLAUDE_MODEL_BACKGROUND` 같은 별도 변수를 둘지 결정한다.

## 009. 소스 seed는 "근거 있는 URL만" + 검증은 스크립트로 분리

- **결정**: `app/db/seed_sources.py`에는 공식·공고문 근거가 있는 URL만 넣고 근거 링크를 `config`에 저장한다. 실제 접속·robots.txt·RSS 파싱 검증은 `scripts/verify_sources.py`로 분리한다.
- **이유**: SPEC의 "추측 URL 금지". 채용 사이트 주소는 자주 바뀐다(예: HD현대·롯데의 캠페인 사이트). 그래서 "왜 이 URL인지"와 "지금도 동작하는지"를 따로 확인할 수 있어야 한다.
- **대안**: 수집 job이 실패하면 그때 비활성화. 하지만 처음부터 robots.txt를 확인하지 않고 요청하게 되므로 채택하지 않음.

## 010. RSS 없는 사이트는 `type=html` + URL 정규식으로 수집 (SPEC 변경)

- **결정**: `source.type` enum에 `html`을 추가했다 (SPEC에는 rss/api/career_portal만 있음). 목록 페이지의 `<a>` 링크 중에서 ① 경로가 소스별 정규식(`config.link_pattern`)과 맞고 ② 제목이 15자 이상인 것만 기사로 본다. 같은 기사에 링크가 여러 개면 제목 태그(h1~h4) 안의 텍스트를 우선한다.
- **이유**: 사용자 결정으로 RSS 없는 6곳도 직접 수집하게 됐다. 사이트별로 CSS 선택자를 짜면 디자인이 바뀔 때마다 깨진다. URL 규칙은 훨씬 덜 바뀐다. LLM을 쓰지 않으니 SPEC 핵심 규칙 3(수집은 일반 코드로)에도 맞는다.
- **대안**: ① 사이트별 CSS 선택자 (정확하지만 깨지기 쉬움) ② LLM으로 목록 추출 (유연하지만 매번 비용이 듦. 채용 포털에만 사용) ③ RSSHub 같은 제3자 피드 (외부 서비스 의존).
- **한계**: JS로 목록을 그리는 페이지는 HTML에 링크가 없다 → M5에서 Playwright 렌더링 후 같은 함수에 넘긴다. 날짜는 목록에 없어서 `first_seen`을 쓴다.
- **마이그레이션 메모**: PostgreSQL enum 값 추가는 `ALTER TYPE ... ADD VALUE`로 직접 작성했다 (autogenerate가 감지하지 못함). 값 삭제는 지원되지 않아서 downgrade는 막아 두었다.
