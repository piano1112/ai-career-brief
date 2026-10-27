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
